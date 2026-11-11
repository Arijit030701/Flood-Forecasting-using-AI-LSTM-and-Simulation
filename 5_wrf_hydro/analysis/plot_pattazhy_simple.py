"""Simple graph: WRF-Hydro daily flow at Pattazhy (ERA5 rain run, IMD rain run) vs measured CAMELS-IND flow, Jun-Aug 2018.
Model daily mean on the Indian day (IST), as in 5_wrf_hydro/analysis/compare_kerala.py."""
import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.dates as mdates
D, OUT = sys.argv[1], sys.argv[2]
plt.rcParams.update({"font.family": "DejaVu Sans"})
def load(f):
    r = pd.read_csv(f, header=None, skipinitialspace=True); r.columns = ['s','time','id','lon','lat','q','qcfs','h']
    r = r[r.id == 2]; r['time'] = pd.to_datetime(r.time)
    r['day'] = (r.time + pd.Timedelta(hours=5, minutes=30)).dt.floor('D')
    return r.groupby('day').q.mean()
imd, era = load(f"{D}/run_imd_frxst.txt"), load(f"{D}/run_era5_frxst.txt")
o = pd.read_csv(f"{D}/observed_2018.csv"); o.index = pd.to_datetime(o[['year','month','day']]); obs = o['15022'].replace(0, np.nan)
s = slice('2018-06-01', '2018-08-31'); imd, era, obs = imd[s], era[s], obs[s]
BLUE, ORANGE, DARK, GRID = "#1f5fae", "#e07b00", "#292929", "#e6e6e6"
fig, ax = plt.subplots(figsize=(11.08, 6.4), dpi=200)
fig.subplots_adjust(left=0.085, right=0.98, top=0.95, bottom=0.1)
ax.axvspan(pd.Timestamp('2018-08-14'), pd.Timestamp('2018-08-18'), color="#f2f2f2", zorder=0)
ax.text(pd.Timestamp('2018-08-16'), 1235, "flood\n14–18 Aug", ha="center", va="top", fontsize=13, color="#777777")
ax.plot(era.index, era.values, color=ORANGE, lw=2, zorder=3)
ax.plot(imd.index, imd.values, color=BLUE, lw=2, zorder=4)
ax.plot(obs.index, obs.values, "o", ms=5.5, color=DARK, zorder=5)
for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
for sp in ["left", "bottom"]: ax.spines[sp].set_color("#9a9a9a")
ax.grid(axis="y", color=GRID, lw=1); ax.set_axisbelow(True)
ax.set_ylim(0, 1250); ax.set_xlim(pd.Timestamp('2018-06-01'), pd.Timestamp('2018-08-31'))
ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=[15]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("1 %b")); ax.xaxis.set_minor_formatter(mdates.DateFormatter("15 %b"))
ax.tick_params(axis="both", which="both", labelsize=13, colors="#4e4e4e", length=0)
ax.set_ylabel("River flow at Pattazhy (m³/s)", fontsize=14, color="#4e4e4e")
# key in the empty top-left corner
from matplotlib.lines import Line2D
h=[Line2D([],[],marker="o",ls="none",ms=7,color=DARK),Line2D([],[],color=BLUE,lw=3),Line2D([],[],color=ORANGE,lw=3)]
leg=ax.legend(h,["measured (daily)","WRF-Hydro with IMD rain","WRF-Hydro with ERA5 rain"],loc="upper left",
              frameon=False,fontsize=15,handlelength=1.8,borderaxespad=0.6,labelspacing=0.6)
for t,c in zip(leg.get_texts(),[DARK,BLUE,ORANGE]): t.set_color(c); t.set_weight("bold")
# peak values
pk = pd.Timestamp('2018-08-16')
ax.text(pk - pd.Timedelta(days=2.6), imd[pk], f"{imd[pk]:.0f}", color=BLUE, fontsize=14, weight="bold", ha="right", va="center")
ax.text(pk - pd.Timedelta(days=2.6), obs[pk] - 15, f"{obs[pk]:.0f}", color=DARK, fontsize=14, weight="bold", ha="right", va="center")
ax.text(pk + pd.Timedelta(days=2.6), era[pk] - 60, f"{era[pk]:.0f}", color=ORANGE, fontsize=14, weight="bold", ha="left", va="center")
fig.savefig(f"{OUT}/wrfhydro_pattazhy_flow_2018.png", facecolor="white")
print("saved", round(imd[pk]), round(obs[pk]), round(era[pk]))
