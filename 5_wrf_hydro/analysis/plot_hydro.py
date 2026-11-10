# Plots river flow at each gauge from WRF-Hydro output.
# Reads frxst_pts_out.txt if it exists, otherwise the hourly *CHANOBS* NetCDF files.
# Usage:  python3 plot_hydro.py  <run folder>  [reference folder]
import sys, os, glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def read_frxst(path):
    rows = []
    for line in open(path):
        t = line.replace(",", " ").split()
        if len(t) < 8:
            continue
        if ":" in t[1] or "_" in t[1]:
            dt, rest = t[1].replace("_", " "), t[2:]
        else:
            dt, rest = t[1] + " " + t[2], t[3:]
        rows.append((pd.to_datetime(dt), rest[0], float(rest[3])))
    return pd.DataFrame(rows, columns=["time", "gauge", "q_cms"])

def read_chanobs(files):
    from netCDF4 import Dataset
    rows = []
    for f in sorted(files):
        t = pd.to_datetime(os.path.basename(f)[:12], format="%Y%m%d%H%M")
        with Dataset(f) as nc:
            v = nc.variables["streamflow"]
            q = v[:].ravel()
            dim = v.dimensions[-1]
            ids = nc.variables[dim][:].ravel() if dim in nc.variables else range(len(q))
            for i, x in zip(ids, q):
                rows.append((t, str(i), float(x)))
    return pd.DataFrame(rows, columns=["time", "gauge", "q_cms"])

def read_any(folder):
    f = glob.glob(os.path.join(folder, "**", "frxst_pts_out.txt"), recursive=True)
    if f:
        print("reading", f[0]); return read_frxst(f[0])
    f = glob.glob(os.path.join(folder, "**", "*CHANOBS*"), recursive=True)
    if f:
        print(f"reading {len(f)} CHANOBS files from {os.path.dirname(f[0])}"); return read_chanobs(f)
    sys.exit(f"No frxst_pts_out.txt or CHANOBS files found in {folder}")

run = sys.argv[1] if len(sys.argv) > 1 else "."
# only look in the run folder itself (not referenceSim inside it)
mine = read_frxst(os.path.join(run, "frxst_pts_out.txt")) if os.path.exists(os.path.join(run, "frxst_pts_out.txt")) \
       else read_chanobs(glob.glob(os.path.join(run, "*CHANOBS*")))
if mine.empty:
    sys.exit("No output found in the run folder - check that the model run finished.")
ref = read_any(sys.argv[2]) if len(sys.argv) > 2 else None

gauges = list(mine.gauge.unique())
ref_gauges = list(ref.gauge.unique()) if ref is not None else []
fig, axes = plt.subplots(len(gauges), 1, figsize=(9, 3 * len(gauges)), squeeze=False)
for k, (ax, g) in enumerate(zip(axes[:, 0], gauges)):
    d = mine[mine.gauge == g]
    ax.plot(d.time, d.q_cms, color="#2a78d6", lw=2, label="my run")
    if ref is not None and ref_gauges:
        rg = g if g in ref_gauges else ref_gauges[min(k, len(ref_gauges) - 1)]
        r = ref[ref.gauge == rg]
        ax.plot(r.time, r.q_cms, color="#eb6834", lw=1.2, ls="--", label="NCAR reference")
    ax.set_title(f"Gauge {g}: peak {d.q_cms.max():.1f} m3/s on {d.time[d.q_cms.idxmax()]:%d %b %H:%M}")
    ax.set_ylabel("Flow (m3/s)")
    ax.grid(alpha=0.3)
    ax.legend()
fig.tight_layout()
fig.savefig("hydrograph.png", dpi=130)
print(mine.groupby("gauge").q_cms.agg(["max", "mean"]).round(2))
print("saved hydrograph.png")
