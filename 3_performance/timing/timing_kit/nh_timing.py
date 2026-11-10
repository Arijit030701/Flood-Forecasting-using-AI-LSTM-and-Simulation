"""Times NeuralHydrology LSTM training on any machine (laptop CPU, CSE server CPU, Colab GPU).

Two fixed benchmarks on real CAMELS-IND data (the quality-controlled data made by nh_multibasin.prepare):
  single : basin 3002 only, LSTM with 20 hidden units, MSE loss, 4 epochs   (the old single-basin setup)
  multi  : 10 basins incl. 3002, LSTM with 128 hidden units, NSE loss, 27 catchment attributes, 2 epochs
           (the multi-basin setup on a 10-basin subset, so a CPU can finish it in well under an hour)
Training 1981-2004, no validation (only training speed is measured). The first epoch includes start-up
costs, so the reported speed is the mean of the later epochs.

Usage:
  python nh_timing.py make-bench <nh_work folder> <bench folder>          (once, where the full data is)
  python nh_timing.py run <bench folder> <results folder> --device cpu --label laptop
  taskset -c 0,2,4,6,8,10,12,14 python nh_timing.py run ... --device cpu --threads 8 --label server_P8
  python nh_timing.py run <bench folder> <results folder> --device cuda:0 --label colab_t4
Output: <results folder>/nh_timing.csv (one line per benchmark and machine)
"""
import argparse, csv, json, os, platform, re, shutil, socket, subprocess, sys, time
from datetime import datetime
from pathlib import Path

import pandas as pd

TARGET = "streamflow_mm_day"
TRAIN = ("01/01/1981", "31/12/2004")


def cpu_name():
    try:
        return [l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")][0]
    except Exception:
        return platform.processor() or "cpu"


def make_bench(work_dir, bench_dir, n=10):
    work, bench = Path(work_dir), Path(bench_dir)
    info = json.loads((work / "prep_info.json").read_text())
    src = Path(info["data_dir"])
    others = sorted(b for b in info["basins"] if b != "3002")
    basins = (["3002"] if "3002" in info["basins"] else []) + others[: n - 1]
    (bench / "data" / "preprocessed").mkdir(parents=True, exist_ok=True)
    for b in basins:
        shutil.copy(src / "preprocessed" / f"{b}.csv", bench / "data" / "preprocessed" / f"{b}.csv")
    attrs = pd.read_csv(src / "attributes.csv", dtype={"gauge_id": str}).set_index("gauge_id")
    attrs.loc[basins].to_csv(bench / "data" / "attributes.csv")
    (bench / "basins_multi.txt").write_text("\n".join(basins) + "\n")
    (bench / "basins_single.txt").write_text(basins[0] + "\n")
    json.dump(dict(basins=basins, dynamic_inputs=info["dynamic_inputs"], static_attributes=info["static_attributes"]),
              open(bench / "bench_info.json", "w"), indent=1)
    size = sum(f.stat().st_size for f in (bench / "data").rglob("*") if f.is_file()) / 1e6
    print(f"Benchmark data: {len(basins)} basins ({', '.join(basins)}), {size:.0f} MB in {bench}")


def _config(name, run_dir, basin_file, data_dir, dyn, stat, hidden, loss, epochs, device):
    s = f"""experiment_name: {name}
run_dir: {run_dir}
train_basin_file: {basin_file}
validation_basin_file: {basin_file}
test_basin_file: {basin_file}
train_start_date: '{TRAIN[0]}'
train_end_date: '{TRAIN[1]}'
validation_start_date: '01/01/2005'
validation_end_date: '31/12/2009'
test_start_date: '01/01/2010'
test_end_date: '31/12/2020'
seed: 1
device: {device}
validate_every: 1000
model: cudalstm
head: regression
output_activation: linear
hidden_size: {hidden}
initial_forget_bias: 3
output_dropout: 0.4
optimizer: Adam
loss: {loss}
learning_rate:
  0: 0.001
batch_size: 256
epochs: {epochs}
clip_gradient_norm: 1
predict_last_n: 1
seq_length: 365
num_workers: 0
log_interval: 5
log_tensorboard: False
log_n_figures: 0
save_weights_every: {epochs}
dataset: camels_ind
data_dir: {data_dir}
dynamic_inputs:
""" + "".join(f"  - {v}\n" for v in dyn) + f"target_variables:\n  - {TARGET}\n"
    if stat:
        s += "static_attributes:\n" + "".join(f"  - {v}\n" for v in stat)
    return s


def _parse_log(log):
    ts = lambda line: datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
    lines = Path(log).read_text().splitlines()
    t_load = next(ts(l) for l in lines if "Loading basin data" in l)
    t_ready = next(ts(l) for l in lines if "Create lookup table" in l)
    ep = [ts(l) for l in lines if re.search(r"Epoch \d+ average loss", l)]
    edges = [t_ready] + ep
    epochs = [(b - a).total_seconds() for a, b in zip(edges[:-1], edges[1:])]
    return (t_ready - t_load).total_seconds(), epochs


def _n_samples(data_dir, basins):
    a, b = (pd.to_datetime(x, dayfirst=True) for x in TRAIN)
    n = 0
    for k in basins:
        q = pd.read_csv(Path(data_dir) / "preprocessed" / f"{k}.csv", index_col="date", parse_dates=["date"])[TARGET]
        n += int(q.loc[a:b].notna().sum())
    return n


def run(bench_dir, out_dir, device, label, threads, which):
    bench, out = Path(bench_dir).resolve(), Path(out_dir).resolve()
    info = json.load(open(bench / "bench_info.json"))
    data = bench / "data"
    cfg_dir, run_dir = out / f"configs_{label}", out / f"runs_{label}"
    cfg_dir.mkdir(parents=True, exist_ok=True); run_dir.mkdir(parents=True, exist_ok=True)
    tests = {
        "single": dict(basins="basins_single.txt", hidden=20, loss="MSE", epochs=4, stat=[]),
        "multi": dict(basins="basins_multi.txt", hidden=128, loss="NSE", epochs=2, stat=info["static_attributes"]),
    }
    env = dict(os.environ)
    if threads:
        env.update(OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads))
    import torch
    print(f"{label}: {cpu_name()} | torch {torch.__version__} | device {device} | "
          f"threads {threads or torch.get_num_threads()}")
    path = out / "nh_timing.csv"
    for name in which:
        t = tests[name]
        basins = (bench / t["basins"]).read_text().split()
        cfg = cfg_dir / f"{name}.yml"
        cfg.write_text(_config(f"{label}_{name}", run_dir, bench / t["basins"], data, info["dynamic_inputs"],
                               t["stat"], t["hidden"], t["loss"], t["epochs"], device))
        print(f"\n== {name}: {len(basins)} basin(s), hidden {t['hidden']}, {t['epochs']} epochs ...", flush=True)
        t0 = time.perf_counter()
        r = subprocess.run(["nh-run", "train", "--config-file", str(cfg)], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        wall = time.perf_counter() - t0
        runs = sorted(run_dir.glob(f"{label}_{name}_*"))
        if r.returncode != 0 or not runs:
            print(r.stderr[-3000:]); sys.exit(f"Training failed for {name}")
        load_s, epochs = _parse_log(runs[-1] / "output.log")
        later = epochs[1:] if len(epochs) > 1 else epochs
        mean_ep = sum(later) / len(later)
        ns = _n_samples(data, basins)
        row = dict(label=label, host=socket.gethostname(), cpu=cpu_name(), device=device,
                   threads=threads or torch.get_num_threads(), test=name, basins=len(basins), hidden=t["hidden"],
                   train_samples=ns, data_load_s=round(load_s, 1), epoch1_s=round(epochs[0], 1),
                   mean_epoch_s=round(mean_ep, 1), samples_per_s=round(ns / mean_ep, 1),
                   epochs=len(epochs), total_wall_s=round(wall, 1))
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row)); new and w.writeheader(); w.writerow(row)
        print(f"   {name}: {mean_ep:.1f} s per epoch ({ns / mean_ep:.0f} samples/s), first epoch {epochs[0]:.1f} s, "
              f"data loading {load_s:.1f} s, total {wall / 60:.1f} min")
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make-bench"); m.add_argument("work_dir"); m.add_argument("bench_dir")
    m.add_argument("--n", type=int, default=10)
    r = sub.add_parser("run"); r.add_argument("bench_dir"); r.add_argument("out_dir")
    r.add_argument("--device", default="cpu"); r.add_argument("--label", default=socket.gethostname())
    r.add_argument("--threads", type=int, default=0); r.add_argument("--tests", nargs="+", default=["single", "multi"])
    a = p.parse_args()
    if a.cmd == "make-bench":
        make_bench(a.work_dir, a.bench_dir, a.n)
    else:
        run(a.bench_dir, a.out_dir, a.device, a.label, a.threads, a.tests)
