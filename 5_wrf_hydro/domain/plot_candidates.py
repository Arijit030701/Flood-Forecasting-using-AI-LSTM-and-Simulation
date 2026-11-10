# Plots observed daily river flow (June-Sept 2018) for a few CAMELS-IND gauges, to check data quality.
# Usage:  python3 plot_candidates.py  <CAMELS-IND folder>  15022 15007 15024 15008
import sys, os, glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root, gauges = sys.argv[1], sys.argv[2:]
flow_file = glob.glob(os.path.join(root, "**", "streamflow_observed.csv"), recursive=True)[0]
q = pd.read_csv(flow_file)
q["date"] = pd.to_datetime(q[["year", "month", "day"]])
q = q[(q.date >= "2018-06-01") & (q.date <= "2018-09-30")].set_index("date")

fig, axes = plt.subplots(len(gauges), 1, figsize=(9, 2.6 * len(gauges)), squeeze=False)
for ax, g in zip(axes[:, 0], gauges):
    s = q[g] if g in q else pd.Series(dtype=float)
    ax.plot(s.index, s.values, color="black", marker=".", ms=3, lw=1)
    ax.axvspan(pd.Timestamp("2018-08-14"), pd.Timestamp("2018-08-18"), color="#eb6834", alpha=0.15)
    ax.set_title(f"Gauge {g}: {s.notna().sum()} of {len(s)} days have data, peak {s.max():.0f}")
    ax.set_ylabel("Flow")
    ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("candidates_2018.png", dpi=120)
print("saved candidates_2018.png  (orange band = 14-18 Aug, the main flood)")
