# Plots WRF-Hydro scaling results (time and speed-up vs number of processes).
# Usage:  python3 plot_scaling.py  timings.csv=label  [other_timings.csv=label ...]
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

colors = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
maxp = 1
for k, arg in enumerate(sys.argv[1:]):
    f, label = arg.split("=", 1) if "=" in arg else (arg, arg)
    d = pd.read_csv(f)
    d = d[d.status == "ok"].groupby("processes", as_index=False).seconds.min()
    t1 = d.loc[d.processes == 1, "seconds"].iloc[0]
    c = colors[k % len(colors)]
    a1.plot(d.processes, d.seconds, "o-", color=c, label=label)
    a2.plot(d.processes, t1 / d.seconds, "o-", color=c, label=label)
    maxp = max(maxp, d.processes.max())
    print(label); print((d.assign(speedup=(t1 / d.seconds).round(2),
                                  efficiency_pct=(100 * t1 / d.seconds / d.processes).round(0))).to_string(index=False))
for ax in (a1, a2):
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 32, 64, 128]); ax.set_xticklabels([1, 2, 4, 8, 16, 32, 64, 128])
    ax.axvline(16, color="grey", ls=":", lw=1)
    ax.set_xlabel("MPI processes (16 per machine)")
    ax.grid(alpha=0.3)
a1.set_yscale("log"); a1.set_ylabel("Run time (s), lower is better"); a1.set_title("(a) Run time")
a2.plot([1, maxp], [1, maxp], "--", color="grey", lw=1, label="ideal")
a2.set_yscale("log", base=2); a2.set_ylabel("Speed-up vs 1 process"); a2.set_title("(b) Speed-up")
a1.text(15, 0.04, "one machine ", transform=a1.get_xaxis_transform(), ha="right", fontsize=8, color="grey")
a1.text(17, 0.04, " several machines", transform=a1.get_xaxis_transform(), ha="left", fontsize=8, color="grey")
a2.legend(fontsize=8)
fig.tight_layout()
fig.savefig("fig_wrfhydro_scaling.png", dpi=150)
print("saved fig_wrfhydro_scaling.png")
