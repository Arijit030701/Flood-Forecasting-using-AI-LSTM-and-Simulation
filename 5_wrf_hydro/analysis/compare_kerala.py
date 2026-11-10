# Compares WRF-Hydro daily river flow with observed CAMELS-IND flow (Kerala 2018), with rain on top.
# Usage (conda OFF, inside the run folder):
#   python3 compare_kerala.py  frxst_pts_out.txt  gauges_snapped.csv  <CAMELS-IND folder>  [FORCING folder] [label]
import sys, os, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

frxst, gauges_csv, camels = sys.argv[1], sys.argv[2], sys.argv[3]
forcing = sys.argv[4] if len(sys.argv) > 4 else None
label = sys.argv[5] if len(sys.argv) > 5 else "WRF-Hydro"
EVAL = ("2018-06-01", "2018-08-31")          # May is spin-up, not scored
FLOOD = ("2018-08-14", "2018-08-18")

# ---- model: hourly flow at the gauges (UTC) -> daily mean on the Indian day (IST)
rows = []
for line in open(frxst):
    t = line.replace(",", " ").split()
    if len(t) < 8:
        continue
    dt, rest = (t[1].replace("_", " "), t[2:]) if (":" in t[1] or "_" in t[1]) else (t[1] + " " + t[2], t[3:])
    rows.append((pd.Timestamp(dt), int(float(rest[0])), float(rest[3])))
m = pd.DataFrame(rows, columns=["time", "fid", "q"])
m["day"] = (m.time + pd.Timedelta(hours=5, minutes=30)).dt.floor("D")
model = m.groupby(["fid", "day"]).q.mean()

g = pd.read_csv(gauges_csv)
site_of = dict(zip(g.FID, g.Site_No.astype(str)))

# ---- observations: daily m3/s, 0 = missing
f = glob.glob(os.path.join(camels, "**", "streamflow_observed.csv"), recursive=True)[0]
q = pd.read_csv(f)
q.index = pd.to_datetime(q[["year", "month", "day"]])

# ---- optional: daily domain-mean rain from the forcing files (mm/day)
rain = None
if forcing:
    from netCDF4 import Dataset
    vals = {}
    for fn in sorted(glob.glob(os.path.join(forcing, "*LDASIN_DOMAIN1"))):
        t = pd.Timestamp(os.path.basename(fn)[:10][:8] + " " + os.path.basename(fn)[8:10] + ":00")
        with Dataset(fn) as nc:
            vals[t] = float(nc["RAINRATE"][:].mean()) * 3600.0
    r = pd.Series(vals)
    rain = r.groupby((r.index + pd.Timedelta(hours=5, minutes=30)).floor("D")).sum()

def scores(s, o):
    ok = s.notna() & o.notna()
    s, o = s[ok].values, o[ok].values
    nse = 1 - np.sum((s - o) ** 2) / np.sum((o - o.mean()) ** 2)
    r = np.corrcoef(s, o)[0, 1]
    kge = 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)
    return dict(days=len(s), NSE=nse, KGE=kge, r=r, bias_pct=100 * (s.mean() / o.mean() - 1))

results = []
fids = sorted(site_of)
fig, axes = plt.subplots(len(fids), 1, figsize=(10, 3.6 * len(fids)), squeeze=False)
for ax, fid in zip(axes[:, 0], fids):
    site = site_of[fid]
    s = model.loc[fid]
    o = q[site].replace(0, np.nan).reindex(s.index) if site in q else pd.Series(np.nan, index=s.index)
    sel = (s.index >= EVAL[0]) & (s.index <= EVAL[1])
    res = dict(gauge=site, **scores(s[sel], o[sel]))
    fl = (s.index >= FLOOD[0]) & (s.index <= FLOOD[1])
    res["flood_peak_obs"] = o[fl].max()
    res["flood_peak_model"] = s[fl].max()
    res["flood_peak_ratio"] = res["flood_peak_model"] / res["flood_peak_obs"]
    res["flood_vol_ratio"] = s[fl & o.notna().values].sum() / o[fl].sum()
    results.append(res)

    ax.axvspan(pd.Timestamp(FLOOD[0]), pd.Timestamp(FLOOD[1]), color="#eb6834", alpha=0.12)
    ax.plot(o.index, o.values, "o", color="black", ms=3, label="observed (CAMELS-IND)")
    ax.plot(s.index, s.values, color="#2a78d6", lw=1.8, label=label)
    ax.axvline(pd.Timestamp(EVAL[0]), color="grey", ls=":", lw=1)
    ax.set_ylabel("Flow (m3/s)")
    ax.set_title(f"Gauge {site}: NSE {res['NSE']:.2f}, KGE {res['KGE']:.2f}, bias {res['bias_pct']:+.0f}%  "
                 f"| flood peak {res['flood_peak_model']:.0f} vs {res['flood_peak_obs']:.0f} m3/s")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    if rain is not None:
        ax2 = ax.twinx()
        ax2.bar(rain.index, rain.values, width=0.9, color="#1baf7a", alpha=0.45)
        ax2.set_ylim(rain.max() * 3, 0)
        ax2.set_ylabel("Rain, domain mean (mm/day)", color="#1baf7a")
fig.tight_layout()
out = f"flow_vs_obs_{label.replace(' ', '_')}.png"
fig.savefig(out, dpi=130)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
tab = pd.DataFrame(results).set_index("gauge").round(2)
tab.to_csv(f"scores_{label.replace(' ', '_')}.csv")
print(f"scored period {EVAL[0]} to {EVAL[1]} (May = spin-up); flood window {FLOOD[0]} to {FLOOD[1]}")
print(tab)
if rain is not None:
    print(f"domain-mean rain: Jun-Aug {rain[EVAL[0]:EVAL[1]].sum():.0f} mm, 14-18 Aug {rain[FLOOD[0]:FLOOD[1]].sum():.0f} mm")
print("saved", out)
