# Compares WRF-Hydro river flow (CHANOBS files) with observed USGS flow and computes NSE, KGE, peak error.
# Usage (inside the run folder):
#   python3 compare_obs.py  <run folder>  <USGS_obs.csv>  <frxst points csv>
import sys, os, glob
import numpy as np
import pandas as pd
from netCDF4 import Dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run, obs_csv, pts_csv = sys.argv[1], sys.argv[2], sys.argv[3]

# ---- model output: one CHANOBS file per hour
rows = []
files = sorted(glob.glob(os.path.join(run, "*CHANOBS*")))
for f in files:
    t = pd.to_datetime(os.path.basename(f)[:12], format="%Y%m%d%H%M")
    with Dataset(f) as nc:
        q = nc.variables["streamflow"][:].ravel()
        lat = nc.variables["latitude"][:].ravel()
        lon = nc.variables["longitude"][:].ravel()
        for k in range(len(q)):
            rows.append((t, k, float(q[k]), float(lat[k]), float(lon[k])))
model = pd.DataFrame(rows, columns=["time", "k", "q", "lat", "lon"])
print(f"model: {len(files)} hourly files, {model.k.nunique()} gauges")

# ---- which real gauge is each model point: match by nearest lat/lon
pts = pd.read_csv(pts_csv, dtype={"Site_No": str})
first = model[model.time == model.time.min()]
site_of = {}
for _, m in first.iterrows():
    d = (pts.LAT - m.lat) ** 2 + (pts.LON - m.lon) ** 2
    site_of[m.k] = pts.loc[d.idxmin(), "Site_No"]
print("model point -> USGS gauge:", site_of)

# ---- observations (every 15 min) -> values at the model's hours
obs = pd.read_csv(obs_csv, dtype={"site_no": str}, parse_dates=["dateTime"])

def nse(s, o):
    return 1 - np.sum((s - o) ** 2) / np.sum((o - o.mean()) ** 2)

def kge(s, o):
    r = np.corrcoef(s, o)[0, 1]
    return 1 - np.sqrt((r - 1) ** 2 + (s.std() / o.std() - 1) ** 2 + (s.mean() / o.mean() - 1) ** 2)

gauges = sorted(site_of)
fig, axes = plt.subplots(len(gauges), 1, figsize=(9, 3.2 * len(gauges)), squeeze=False)
results = []
for ax, k in zip(axes[:, 0], gauges):
    site = site_of[k]
    m = model[model.k == k].set_index("time").q
    o = obs[obs.site_no == site].set_index("dateTime").streamflow_cms.sort_index()
    o = o[~o.index.duplicated()]
    o_h = o.reindex(o.index.union(m.index)).interpolate(method="time").reindex(m.index)
    ok = o_h.notna()
    s, ob = m[ok].values, o_h[ok].values
    res = dict(gauge=site, hours=int(ok.sum()), NSE=nse(s, ob), KGE=kge(s, ob),
               peak_obs=ob.max(), peak_model=s.max(),
               peak_error_pct=100 * (s.max() / ob.max() - 1),
               peak_time_diff_h=(m[ok].idxmax() - o_h[ok].idxmax()).total_seconds() / 3600,
               volume_bias_pct=100 * (s.sum() / ob.sum() - 1))
    results.append(res)
    ax.plot(o.index, o.values, color="black", lw=1.2, label="observed (USGS)")
    ax.plot(m.index, m.values, color="#2a78d6", lw=2, label="WRF-Hydro")
    ax.set_xlim(m.index.min(), m.index.max())
    ax.set_title(f"USGS {site}:  NSE {res['NSE']:.2f},  KGE {res['KGE']:.2f},  "
                 f"peak {res['peak_model']:.1f} vs {res['peak_obs']:.1f} m3/s observed")
    ax.set_ylabel("Flow (m3/s)")
    ax.grid(alpha=0.3)
    ax.legend()
fig.tight_layout()
fig.savefig("hydrograph_vs_obs.png", dpi=130)

table = pd.DataFrame(results).set_index("gauge").round(2)
table.to_csv("scores_vs_obs.csv")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
print(table)
print("saved hydrograph_vs_obs.png and scores_vs_obs.csv")
