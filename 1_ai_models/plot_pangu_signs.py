"""Pangu-Weather warning signs against flood size, 5 Indian floods.

Data: 1_ai_models/pangu.ipynb, section 8 (change = mean of the last 24 h minus mean of the
first 24 h of each forecast, at the grid cell nearest the city) and section 9 (Pearson r, p).
Observed rain is the reported gauge total for each flood window (24 h, 6 h or 3 days) and is
only used as a measure of how big each flood was.
"""
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from scipy import stats

floods = [  # name, observed rain (mm), pressure change (hPa), humidity change at 850 hPa (g/kg)
    ("Delhi 2023", 153, -1.06, 1.11),
    ("Chennai 2015", 286, -1.26, 0.72),
    ("Mumbai 2024", 300, 1.17, 0.25),
    ("Idukki 2018", 588, 0.35, -0.53),
    ("Mumbai 2005", 944, -2.46, 0.17),
]
names = [f[0] for f in floods]
rain = np.array([f[1] for f in floods], float)
dp = np.array([f[2] for f in floods])
dq = np.array([f[3] for f in floods])

BLUE, ORANGE = "#1f5fae", "#d9822b"
INK, MUTED, GRID = "#222222", "#666666", "#e6e6e6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "axes.edgecolor": "#bbbbbb",
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})

fig, axes = plt.subplots(1, 2, figsize=(10.4, 6.0), dpi=200)
panels = [
    (axes[0], dp, "Pressure change (hPa)", "falling pressure = warning", -1, (-3.0, 1.8),
     {"Delhi 2023": (8, 8), "Chennai 2015": (8, -16), "Mumbai 2024": (8, 6), "Idukki 2018": (8, 6), "Mumbai 2005": (-10, 10)}),
    (axes[1], dq, "Humidity change at 850 hPa (g/kg)", "rising humidity = warning", +1, (-0.9, 1.45),
     {"Delhi 2023": (8, 6), "Chennai 2015": (8, 6), "Mumbai 2024": (8, -16), "Idukki 2018": (8, -16), "Mumbai 2005": (-10, 10)}),
]
for ax, y, title, warn_txt, warn_sign, ylim, offs in panels:
    r, p = stats.pearsonr(rain, y)
    # shade the half where the change is a warning sign
    lo, hi = ylim
    if warn_sign < 0:
        ax.axhspan(lo, 0, color=BLUE, alpha=0.06, lw=0)
        ax.text(80, lo + 0.05 * (hi - lo), warn_txt, ha="left", va="bottom", fontsize=12.5, color=BLUE)
    else:
        ax.axhspan(0, hi, color=BLUE, alpha=0.06, lw=0)
        ax.text(1010, hi - 0.06 * (hi - lo), warn_txt, ha="right", va="top", fontsize=12.5, color=BLUE)
    ax.axhline(0, color="#999999", lw=1)
    # least-squares line, only to show the direction of r
    k, b = np.polyfit(rain, y, 1)
    xx = np.array([100, 1000])
    ax.plot(xx, k * xx + b, color="#9a9a9a", lw=2, ls=(0, (5, 4)), zorder=2)
    for n, xv, yv in zip(names, rain, y):
        good = (yv < 0) if warn_sign < 0 else (yv > 0)
        if good:
            ax.scatter(xv, yv, s=150, color=BLUE, edgecolor="white", linewidth=2, zorder=4)
        else:
            ax.scatter(xv, yv, s=150, facecolor="white", edgecolor=ORANGE, linewidth=3, zorder=4)
        dx, dy = offs[n]
        ax.annotate(f"{n}\n{yv:+.2f}".replace("-", "\u2212"), (xv, yv), xytext=(dx, dy), textcoords="offset points",
                    ha="right" if dx < 0 else "left", va="bottom" if dy > 0 else "top",
                    fontsize=12, color=INK, linespacing=1.1, zorder=5,
                    path_effects=[pe.withStroke(linewidth=4, foreground="white")])
    ax.set_xlim(60, 1040)
    ax.set_ylim(*ylim)
    ax.set_xticks([200, 400, 600, 800, 1000])
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Flood size: observed rain (mm)", fontsize=13.5, color=MUTED)
    ax.set_title(title, loc="left", fontsize=15.5, fontweight="bold", color=INK, pad=26)
    ax.text(0, 1.015, f"r = {r:.2f},  p = {p:.2f}".replace("-", "\u2212"), transform=ax.transAxes, fontsize=13, color=MUTED, va="bottom")
    print(title, round(r, 3), round(p, 3))

from matplotlib.lines import Line2D
handles = [Line2D([], [], marker="o", ls="", ms=11, mfc=BLUE, mec="white", mew=2),
           Line2D([], [], marker="o", ls="", ms=10, mfc="white", mec=ORANGE, mew=3),
           Line2D([], [], color="#9a9a9a", lw=2, ls=(0, (5, 4)))]
fig.legend(handles, ["sign pointed to rain", "sign pointed the other way", "trend across the 5 floods"],
           loc="lower center", ncol=3, frameon=False, fontsize=12.5, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.06, 1, 1), w_pad=3)
out = "pangu_signs_vs_flood_size.png"
fig.savefig(out, facecolor="white")
print("saved", out)
