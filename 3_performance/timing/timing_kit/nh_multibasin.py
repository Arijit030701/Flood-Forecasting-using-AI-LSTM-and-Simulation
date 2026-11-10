"""Multi-basin LSTM on CAMELS-IND with NeuralHydrology (helpers used by the Colab notebook).

Steps
  1. prepare()        raw CAMELS-IND -> NeuralHydrology layout -> streamflow quality control ->
                      basin selection -> input / attribute selection        (data_dir: <work>/camels_ind_qc)
  2. write_configs()  YAML files for the multi-basin model and the single-basin comparison models
  3. analyse()        test scores per basin, single vs multi comparison, figures and tables

Rain input: CAMELS-IND's `prcp` is the IMD 0.25 deg gauge-based gridded rainfall averaged over each
catchment, so the model is driven by IMD rainfall averaged over the catchment (not one grid cell).
"""
import glob
import json
import os
import pickle
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "streamflow_mm_day"
PERIODS = dict(train=("01/01/1981", "31/12/2004"),
               validation=("01/01/2005", "31/12/2009"),
               test=("01/01/2010", "31/12/2020"))

# ---------------------------------------------------------------- static attributes
# Concepts to look for (first matching column name wins). Streamflow signatures are never used,
# because they are computed from the very flow the model has to predict.
ATTR_CONCEPTS = [
    ["cwc_area", "area"], ["elev_mean", "elev"], ["slope_mean", "slope"], ["dpsbar", "drainage"],
    ["p_mean", "prec_mean", "precip_mean"], ["pet_mean"], ["aridity"], ["p_seasonality", "seasonality"],
    ["asynchronicity", "asynch"], ["high_prec_freq"], ["high_prec_dur"], ["low_prec_freq", "dry_day"],
    ["low_prec_dur"], ["frac_forest", "forest"], ["crop", "agri"], ["urban", "built"], ["water_frac", "water"],
    ["lai_max", "lai"], ["sand"], ["silt"], ["clay"], ["soil_depth", "depth"], ["awc", "water_storage", "available"],
    ["conductivity", "ksat"], ["porosity"], ["permeab"], ["dam_count", "num_dams", "dams"],
    ["storage", "reservoir"], ["pop", "population"],
]
SIGNATURE_WORDS = ["q_mean", "runoff", "baseflow", "bfi", "flow", "elasticity", "fdc", "gini", "hfd",
                   "q5", "q95", "zero_q", "high_q", "low_q", "streamflow", "discharge"]
SKIP_WORDS = ["gauge", "lat", "lon", "id", "name", "code", "state", "river", "basin_name"]


def _find_base(raw_dir: Path) -> Path:
    for p in [raw_dir] + sorted(raw_dir.rglob("*")):
        if p.is_dir() and (p / "catchment_mean_forcings").is_dir() and (p / "attributes_csv").is_dir():
            return p
    raise FileNotFoundError(f"No folder with catchment_mean_forcings/ and attributes_csv/ inside {raw_dir}")


def _read_attribute_tables(base: Path) -> tuple[pd.DataFrame, dict]:
    tables, origin = [], {}
    for f in sorted((base / "attributes_csv").glob("*.csv")):
        df = pd.read_csv(f)
        if "gauge_id" not in df.columns:
            continue
        df["gauge_id"] = df["gauge_id"].astype(str)
        df = df.drop_duplicates("gauge_id").set_index("gauge_id")
        for c in df.columns:
            origin.setdefault(c, f.stem)
        tables.append(df)
    attrs = pd.concat(tables, axis=1)
    attrs = attrs.loc[:, ~attrs.columns.duplicated()]
    return attrs, origin


def _pick_attributes(attrs: pd.DataFrame, origin: dict, basins: list, max_nan=0.10) -> list:
    sub = attrs.loc[basins]
    numeric = [c for c in sub.columns if pd.api.types.is_numeric_dtype(sub[c])]

    def usable(c):
        lc, lo = c.lower(), origin.get(c, "").lower()
        if any(w in lc for w in SIGNATURE_WORDS) or "hydro" in lo or "signature" in lo:
            return False
        if any(lc == w or lc.startswith(w + "_") or lc.endswith("_" + w) for w in SKIP_WORDS):
            return False
        col = sub[c]
        return col.isna().mean() <= max_nan and col.std(skipna=True) > 0

    chosen = []
    for concept in ATTR_CONCEPTS:
        for key in concept:
            hits = [c for c in numeric if key in c.lower() and usable(c) and c not in chosen]
            if hits:
                chosen.append(sorted(hits, key=len)[0])
                break
    if len(chosen) < 8:                      # unknown naming: fall back to the most complete columns
        extra = [c for c in numeric if usable(c) and c not in chosen]
        extra = sorted(extra, key=lambda c: sub[c].isna().mean())[: 25 - len(chosen)]
        chosen += extra
    return chosen


# ---------------------------------------------------------------- quality control
def qc_streamflow(df: pd.DataFrame, rain_col: str):
    """Returns cleaned flow and a dict of counts. Flags:
       negative values; identical extreme values repeated on separate days (the 946.46722 mm/day case);
       daily flow more than 100 mm above the rain of the previous 7 days (impossible without a data error)."""
    q = df[TARGET].astype(float).copy()
    n_obs = int(q.notna().sum())
    flags = pd.Series(False, index=q.index)
    neg = q < 0
    flags |= neg
    rep = pd.Series(False, index=q.index)
    if n_obs > 100:
        thr = q.quantile(0.999)
        big = q[(q >= thr) & (q > 20)]
        counts = big.round(5).value_counts()
        rep_vals = counts[counts >= 2].index
        rep = q.round(5).isin(rep_vals) & (q > 20)
        flags |= rep
    rain7 = df[rain_col].rolling(7, min_periods=1).sum() if rain_col in df else None
    over = (q > rain7 + 100) if rain7 is not None else pd.Series(False, index=q.index)
    flags |= over.fillna(False)
    q[flags] = np.nan
    return q, dict(n_obs=n_obs, negative=int(neg.sum()), repeated_extreme=int(rep.sum()),
                   flow_above_rain=int(over.fillna(False).sum()), removed=int(flags.sum()))


def _count_valid(q: pd.Series, period: str) -> int:
    a, b = (pd.to_datetime(x, dayfirst=True) for x in PERIODS[period])
    return int(q.loc[a:b].notna().sum())


def prepare(raw_dir: str, work_dir: str, min_train_days=3 * 365, min_test_days=365, max_runoff_ratio=1.0):
    from neuralhydrology.datasetzoo.camelsind import preprocess_camels_ind_dataset
    raw_dir, work = Path(raw_dir), Path(work_dir)
    base = _find_base(raw_dir)
    proc = work / "camels_ind_proc"
    if not (proc / "preprocessed").is_dir():
        if proc.exists():
            shutil.rmtree(proc)
        preprocess_camels_ind_dataset(str(base), str(proc))
    qc_dir = work / "camels_ind_qc"
    (qc_dir / "preprocessed").mkdir(parents=True, exist_ok=True)

    files = sorted((proc / "preprocessed").glob("*.csv"))
    sample = pd.read_csv(files[0], nrows=5)
    rain_col = next((c for c in sample.columns if c.lower() in ("prcp", "precipitation", "prec", "rain")),
                    next((c for c in sample.columns if c.lower().startswith("prcp")), None))
    print(f"{len(files)} basin files; rain column: {rain_col}")

    report, data = [], {}
    for f in files:
        df = pd.read_csv(f, index_col="date", parse_dates=["date"])
        if TARGET not in df or df[TARGET].notna().sum() == 0:
            continue
        q, counts = qc_streamflow(df, rain_col)
        df[TARGET] = q
        both = df[[TARGET, rain_col]].dropna()
        rr = both[TARGET].mean() / both[rain_col].mean() if len(both) > 365 and both[rain_col].mean() > 0 else np.nan
        row = dict(basin=f.stem, **counts, runoff_ratio=round(float(rr), 3) if rr == rr else np.nan,
                   train_days=_count_valid(q, "train"), val_days=_count_valid(q, "validation"),
                   test_days=_count_valid(q, "test"))
        reason = []
        if row["train_days"] < min_train_days:
            reason.append("short train record")
        if row["test_days"] < min_test_days:
            reason.append("short test record")
        if not (rr <= max_runoff_ratio):
            reason.append("runoff ratio > 1 or unknown")
        row["kept"] = not reason
        row["reason"] = "; ".join(reason)
        report.append(row)
        data[f.stem] = df

    rep = pd.DataFrame(report)
    rep.to_csv(work / "qc_report.csv", index=False)
    basins = rep.loc[rep.kept, "basin"].tolist()
    print(f"Quality control: {int(rep.removed.sum())} flow values removed in {int((rep.removed > 0).sum())} basins "
          f"(negative {int(rep.negative.sum())}, repeated extremes {int(rep.repeated_extreme.sum())}, "
          f"flow > 7-day rain + 100 mm {int(rep.flow_above_rain.sum())})")
    print(f"Basins with flow: {len(rep)}; kept: {len(basins)}; dropped: "
          + ", ".join(f"{k} ({v})" for k, v in rep.loc[~rep.kept, "reason"].value_counts().items()))
    if "3002" in data:
        r = rep.set_index("basin").loc["3002"]
        print(f"Basin 3002: removed {r.removed} values (repeated extremes {r.repeated_extreme}); kept={r.kept}")

    # dynamic inputs: every forcing column that is complete for the kept basins
    cols = [c for c in data[basins[0]].columns if c != TARGET]
    a, b = pd.Timestamp("1980-01-01"), pd.Timestamp("2020-12-31")
    nan_frac = {c: np.mean([data[k].loc[a:b, c].isna().mean() for k in basins]) for c in cols}
    dyn = [c for c in cols if nan_frac[c] < 0.01]
    print(f"Dynamic inputs ({len(dyn)}): {dyn}")
    if len(dyn) < len(cols):
        print(f"  left out (incomplete): {[c for c in cols if c not in dyn]}")
    for k in basins:
        data[k][dyn + [TARGET]].to_csv(qc_dir / "preprocessed" / f"{k}.csv")

    attrs, origin = _read_attribute_tables(base)
    stat = _pick_attributes(attrs, origin, basins)
    out = attrs.loc[basins, stat].copy()
    out = out.fillna(out.median(numeric_only=True))
    out.index.name = "gauge_id"
    out.to_csv(qc_dir / "attributes.csv")
    print(f"Static attributes ({len(stat)}): {stat}")

    (work / "basins_all.txt").write_text("\n".join(basins) + "\n")
    info = dict(basins=basins, dynamic_inputs=dyn, static_attributes=stat, rain_col=rain_col,
                data_dir=str(qc_dir))
    (work / "prep_info.json").write_text(json.dumps(info, indent=1))
    return info


# ---------------------------------------------------------------- configs
def _yaml_list(x):
    return "\n".join(f"  - {v}" for v in x)


def _config(name, run_dir, basin_file, data_dir, dyn, stat, hidden, loss, epochs, lr, device, seed,
            num_workers, validate_n=None):
    s = f"""experiment_name: {name}
run_dir: {run_dir}
train_basin_file: {basin_file}
validation_basin_file: {basin_file}
test_basin_file: {basin_file}
train_start_date: '{PERIODS['train'][0]}'
train_end_date: '{PERIODS['train'][1]}'
validation_start_date: '{PERIODS['validation'][0]}'
validation_end_date: '{PERIODS['validation'][1]}'
test_start_date: '{PERIODS['test'][0]}'
test_end_date: '{PERIODS['test'][1]}'
seed: {seed}
device: {device}
validate_every: 5
{"validate_n_random_basins: " + str(validate_n) if validate_n else ""}
metrics:
  - NSE
  - KGE
model: cudalstm
head: regression
output_activation: linear
hidden_size: {hidden}
initial_forget_bias: 3
output_dropout: 0.4
optimizer: Adam
loss: {loss}
learning_rate:
{chr(10).join(f'  {k}: {v}' for k, v in lr.items())}
batch_size: 256
epochs: {epochs}
clip_gradient_norm: 1
predict_last_n: 1
seq_length: 365
num_workers: {num_workers}
log_interval: 5
log_tensorboard: False
log_n_figures: 0
save_weights_every: {epochs}
dataset: camels_ind
data_dir: {data_dir}
dynamic_inputs:
{_yaml_list(dyn)}
target_variables:
  - {TARGET}
clip_targets_to_zero:
  - {TARGET}
"""
    if stat:
        s += "static_attributes:\n" + _yaml_list(stat) + "\n"
    return s


def write_configs(work_dir, run_dir, device="cuda:0", n_single=10, single_extra=("3002",), seeds=(1,),
                  multi_hidden=128, multi_epochs=30, single_epochs=50, num_workers=2, rng_seed=0):
    work = Path(work_dir); info = json.loads((work / "prep_info.json").read_text())
    cfg_dir = work / "configs"; cfg_dir.mkdir(exist_ok=True)
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    for sd in seeds:
        p = cfg_dir / f"multi_seed{sd}.yml"
        p.write_text(_config(f"multi_seed{sd}", run_dir, work / "basins_all.txt", info["data_dir"],
                             info["dynamic_inputs"], info["static_attributes"], multi_hidden, "NSE",
                             multi_epochs, {0: 1e-3, int(multi_epochs * 0.6): 5e-4, int(multi_epochs * 0.85): 1e-4},
                             device, sd, num_workers, validate_n=min(50, len(info["basins"]))))
        paths.append(p)
    rnd = random.Random(rng_seed)
    singles = [b for b in single_extra if b in info["basins"]]
    singles += rnd.sample([b for b in info["basins"] if b not in singles], min(n_single, len(info["basins"]) - len(singles)))
    for b in singles:
        bf = cfg_dir / f"basin_{b}.txt"; bf.write_text(b + "\n")
        p = cfg_dir / f"single_{b}.yml"
        p.write_text(_config(f"single_{b}", run_dir, bf, info["data_dir"], info["dynamic_inputs"], [], 20, "MSE",
                             single_epochs, {0: 1e-2, int(single_epochs * 0.6): 5e-3, int(single_epochs * 0.8): 1e-3},
                             device, 1, num_workers))
        paths.append(p)
    (work / "single_basins.txt").write_text("\n".join(singles) + "\n")
    print(f"Wrote {len(paths)} configs in {cfg_dir}: multi-basin x{len(seeds)}, single-basin x{len(singles)} "
          f"({', '.join(singles)})")
    return paths


# ---------------------------------------------------------------- analysis
def _metrics(obs, sim):
    m = ~np.isnan(obs) & ~np.isnan(sim)
    o, s = obs[m], sim[m]
    if len(o) < 30 or np.var(o) == 0:
        return dict(n=int(len(o)), NSE=np.nan, KGE=np.nan, r=np.nan)
    nse = 1 - np.sum((s - o) ** 2) / np.sum((o - o.mean()) ** 2)
    r = np.corrcoef(o, s)[0, 1] if np.std(s) > 0 else 0.0
    alpha = np.std(s) / np.std(o); beta = s.mean() / o.mean() if o.mean() != 0 else np.nan
    kge = 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)
    return dict(n=int(len(o)), NSE=nse, KGE=kge, r=r)


def _latest_run(run_dir, name):
    runs = sorted(glob.glob(os.path.join(run_dir, f"{name}_*")))
    return Path(runs[-1]) if runs else None


def _load_test(run):
    files = sorted(run.glob("test/model_epoch*/test_results.p"))
    if not files:
        return None
    with open(files[-1], "rb") as fh:
        res = pickle.load(fh)
    out = {}
    for b, d in res.items():
        xr = d["1D"]["xr"]
        obs = xr[f"{TARGET}_obs"].values[:, -1]; sim = xr[f"{TARGET}_sim"].values[:, -1]
        out[b] = pd.DataFrame({"obs": obs, "sim": sim}, index=pd.to_datetime(xr["date"].values))
    return out


def analyse(work_dir, run_dir, out_dir, window_3002=("2017-01-01", "2018-10-08")):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    work, out = Path(work_dir), Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    singles = (work / "single_basins.txt").read_text().split()

    multi_runs = sorted({Path(p).name.rsplit("_", 2)[0] for p in glob.glob(os.path.join(run_dir, "multi_seed*"))})
    multi = [_load_test(_latest_run(run_dir, n)) for n in multi_runs]
    multi = [m for m in multi if m]
    if not multi:
        raise RuntimeError("No evaluated multi-basin run found (run nh-run evaluate first).")
    basins = sorted(multi[0])
    ens = {b: pd.DataFrame({"obs": multi[0][b]["obs"],
                            "sim": np.mean([m[b]["sim"].values for m in multi], axis=0)}, index=multi[0][b].index)
           for b in basins}
    rows = [dict(basin=b, model=f"multi-basin ({len(multi)} seed{'s' if len(multi) > 1 else ''})",
                 **_metrics(ens[b]["obs"].values, ens[b]["sim"].values)) for b in basins]
    single = {}
    for b in singles:
        run = _latest_run(run_dir, f"single_{b}")
        res = _load_test(run) if run else None
        if res and b in res:
            single[b] = res[b]
            rows.append(dict(basin=b, model="single-basin", **_metrics(res[b]["obs"].values, res[b]["sim"].values)))
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "test_scores_per_basin.csv", index=False)

    mname = tab.model.iloc[0]
    m_all = tab[tab.model == mname]
    m_sub = m_all[m_all.basin.isin(single)]
    s_sub = tab[tab.model == "single-basin"]
    summ = pd.DataFrame([
        dict(group=f"Multi-basin, all {len(m_all)} basins", **{f"median_{k}": m_all[k].median() for k in ["NSE", "KGE", "r"]},
             share_NSE_gt_0=(m_all.NSE > 0).mean(), share_NSE_gt_05=(m_all.NSE > 0.5).mean()),
        dict(group=f"Multi-basin, the {len(m_sub)} comparison basins", **{f"median_{k}": m_sub[k].median() for k in ["NSE", "KGE", "r"]},
             share_NSE_gt_0=(m_sub.NSE > 0).mean(), share_NSE_gt_05=(m_sub.NSE > 0.5).mean()),
        dict(group=f"Single-basin, the same {len(s_sub)} basins", **{f"median_{k}": s_sub[k].median() for k in ["NSE", "KGE", "r"]},
             share_NSE_gt_0=(s_sub.NSE > 0).mean(), share_NSE_gt_05=(s_sub.NSE > 0.5).mean()),
    ])
    summ.to_csv(out / "summary.csv", index=False)
    pd.set_option("display.width", 160)
    print(f"\nTest period {PERIODS['test'][0]} - {PERIODS['test'][1]}\n")
    print(summ.round(3).to_string(index=False))

    pair = m_sub.merge(s_sub, on="basin", suffixes=("_multi", "_single"))
    if len(pair):
        print(f"\nMulti-basin better than single-basin (NSE) in {(pair.NSE_multi > pair.NSE_single).sum()} "
              f"of {len(pair)} basins")
        print(pair[["basin", "NSE_single", "NSE_multi", "KGE_single", "KGE_multi"]].round(3).to_string(index=False))

    if "3002" in ens:
        a, b = window_3002
        print(f"\nBasin 3002, {a} to {b} (same window as the FNL / CAMELS-IND single-basin study):")
        lines = [("multi-basin", ens["3002"])] + ([("single-basin", single["3002"])] if "3002" in single else [])
        for nm, d in lines:
            m = _metrics(d.loc[a:b, "obs"].values, d.loc[a:b, "sim"].values)
            print(f"  {nm:13s} NSE {m['NSE']:.3f}  KGE {m['KGE']:.3f}  r {m['r']:.3f}  (n={m['n']})")
        print("  earlier study, setup C (CAMELS-IND inputs, 4 training years): NSE -0.193  KGE 0.380")
        fig, ax = plt.subplots(figsize=(9, 3.4))
        d = ens["3002"].loc[a:b]
        ax.plot(d.index, d.obs, color="#0b0b0b", lw=1.2, label="Observed (quality-controlled)")
        if "3002" in single:
            ax.plot(d.index, single["3002"].loc[a:b, "sim"], color="#eb6834", lw=1.2, label="Single-basin LSTM")
        ax.plot(d.index, d.sim, color="#2a78d6", lw=1.4, label="Multi-basin LSTM")
        ax.set_ylabel("Flow (mm/day)"); ax.grid(color="#e4e3df"); ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="upper left"); ax.set_title("Basin 3002, test period", loc="left")
        fig.tight_layout(); fig.savefig(out / "fig_nh_3002_hydrograph.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for d, c, lab in [(m_all, "#2a78d6", f"Multi-basin, all {len(m_all)} basins"),
                      (m_sub, "#1baf7a", f"Multi-basin, {len(m_sub)} comparison basins"),
                      (s_sub, "#eb6834", f"Single-basin, same {len(s_sub)} basins")]:
        v = np.sort(d.NSE.clip(lower=-1).dropna().values)
        if len(v):
            ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=c, lw=2, label=lab)
    ax.axvline(0, color="#8a8984", lw=1, ls="--")
    ax.set_xlim(-1, 1); ax.set_xlabel("Test NSE (values below -1 shown at -1)"); ax.set_ylabel("Share of basins")
    ax.grid(color="#e4e3df"); ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, loc="upper left")
    ax.set_title("Test NSE across basins (further right = better)", loc="left")
    fig.tight_layout(); fig.savefig(out / "fig_nh_nse_cdf.png", dpi=200); plt.close(fig)
    print(f"\nSaved tables and figures in {out}")
    return summ
