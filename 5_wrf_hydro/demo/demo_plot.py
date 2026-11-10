# Plots the live demo: hourly river flow from WRF-Hydro against measured daily flow, with the rain.
# Usage (conda OFF): python3 demo_plot.py frxst_pts_out.txt gauges_snapped.csv <CAMELS-IND folder> FORCING 2018-08-08 2018-08-21
import sys, os, glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from netCDF4 import Dataset

frx, gcsv, camels, forcing, d0, d1 = sys.argv[1:7]
IST = pd.Timedelta(hours=5, minutes=30)
t0, t1 = pd.Timestamp(d0), pd.Timestamp(d1) + pd.Timedelta(days=1)

# model: hourly flow at each gauge (file is in UTC; shown in Indian time)
rows = []
for line in open(frx):
    t = line.replace(",", " ").split()
    if len(t) < 8:
        continue
    dt, rest = (t[1].replace("_", " "), t[2:]) if (":" in t[1] or "_" in t[1]) else (t[1] + " " + t[2], t[3:])
    rows.append((pd.Timestamp(dt) + IST, int(float(rest[0])), float(rest[3])))
m = pd.DataFrame(rows, columns=["time", "fid", "q"])

g = pd.read_csv(gcsv)
site = {int(a): str(b) for a, b in zip(g.FID, g.Site_No)}

# measured: CAMELS-IND daily flow in m3/s (0 = missing)
q = pd.read_csv(glob.glob(os.path.join(camels, "**", "streamflow_observed.csv"), recursive=True)[0])
q.index = pd.to_datetime(q[["year", "month", "day"]])

# rain: domain-mean rain per hour over the plot window (mm/h)
rain = {}
for f in sorted(glob.glob(os.path.join(forcing, "*LDASIN_DOMAIN1"))):
    b = os.path.basename(f)
    t = pd.Timestamp(b[:8] + " " + b[8:10] + ":00") + IST
    if t0 <= t <= t1:
        with Dataset(f) as nc:
            rain[t] = float(nc["RAINRATE"][:].mean()) * 3600.0
rain = pd.Series(rain).sort_index()

names = {"15022": "Kallada river at Pattazhy (gauge 15022)", "15007": "Gauge 15007 (no dams)"}
order = sorted(site, key=lambda f: site[f] != "15022")          # Pattazhy first
fig, axes = plt.subplots(len(order) + 1, 1, figsize=(10, 2.4 + 3.2 * len(order)), sharex=True,
                         gridspec_kw=dict(height_ratios=[1] + [2] * len(order)))
axes[0].bar(rain.index, rain.values, width=1 / 24, color="#1baf7a")
axes[0].set_ylabel("Rain (mm/h)")
axes[0].set_title("WRF-Hydro live demo: the Kerala flood of August 2018 (rain = IMD, mean over the domain)")
for ax, fid in zip(axes[1:], order):
    s = site[fid]
    mm = m[m.fid == fid].set_index("time").q
    md = mm.groupby(mm.index.floor("D")).mean()                    # model daily mean, Indian day
    o = q[s].replace(0, np.nan)[t0:t1] if s in q else pd.Series(dtype=float)
    ax.plot(mm.index, mm.values, color="#2a78d6", lw=1.8, label="WRF-Hydro, hourly")
    ax.step(md.index + pd.Timedelta(hours=12), md.values, where="mid", color="#2a78d6", ls="--", lw=1,
            label="WRF-Hydro, daily mean")
    ax.plot(o.index + pd.Timedelta(hours=12), o.values, "o", color="black", ms=6, label="measured, daily mean (CWC)")
    pk = md.idxmax()                                             # day of the model's flood peak
    around = o.reindex(pd.date_range(pk - pd.Timedelta(days=1), pk + pd.Timedelta(days=1), freq="D"))
    if around.notna().all():
        txt = f"daily-mean peak: model {md.max():.0f} vs measured {o.max():.0f} m3/s"
    else:
        txt = "measured flow missing on the flood days"
    ax.set_title(f"{names.get(s, s)}: {txt}")
    print(f"{names.get(s, s)}: hourly model peak {mm.max():.0f} m3/s at {mm.idxmax():%d %b %H:%M} IST; {txt}")
    ax.set_ylabel("Flow (m3/s)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
axes[-1].set_xlim(t0, t1)
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig("demo_flood.png", dpi=130)
print("saved demo_flood.png")
