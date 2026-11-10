# Checks the routing grid made by the GIS tool: river channels, basin and gauge points.
# Usage:  python3 plot_fulldom.py  Fulldom_hires.nc
import sys
import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

nc = Dataset(sys.argv[1])
print("variables:", ", ".join(nc.variables))
lat, lon = nc["LATITUDE"][:], nc["LONGITUDE"][:]
topo = np.ma.masked_less(nc["TOPOGRAPHY"][:], -100)
chan = nc["CHANNELGRID"][:]
order = nc["STREAMORDER"][:] if "STREAMORDER" in nc.variables else None
frx = nc["frxst_pts"][:]
basin = nc["basn_msk"][:] if "basn_msk" in nc.variables else None
print(f"routing grid {topo.shape[1]} x {topo.shape[0]} cells")
print(f"channel cells: {(chan >= 0).sum()}")
if basin is not None:
    for b in np.unique(basin[basin > 0]):
        print(f"basin {int(b)}: {(basin == b).sum()} cells")

fig, ax = plt.subplots(figsize=(7.5, 7))
ax.pcolormesh(lon, lat, topo, cmap="Greys_r", shading="auto", alpha=0.8)
if basin is not None:
    ax.contour(lon, lat, (basin > 0).astype(int), levels=[0.5], colors="#eda100", linewidths=2)
ch = np.ma.masked_where(chan < 0, order if order is not None else np.ones_like(chan))
ax.pcolormesh(lon, lat, ch, cmap="Blues", vmin=0, shading="auto")
jj, ii = np.where(frx >= 0)
for j, i in zip(jj, ii):
    on = chan[j, i] >= 0
    ax.plot(lon[j, i], lat[j, i], "o", ms=9, color="#1baf7a" if on else "red", mec="white")
    ax.annotate(f"gauge {int(frx[j, i])}" + ("" if on else " (NOT on channel!)"), (lon[j, i], lat[j, i]),
                xytext=(6, 6), textcoords="offset points", color="black", weight="bold")
    print(f"gauge {int(frx[j, i])} at {lat[j, i]:.4f} N {lon[j, i]:.4f} E -> on channel: {on}")
ax.set_title("Routing grid: channels (blue), gauge basins (yellow), gauges")
ax.set_xlabel("Longitude (E)")
ax.set_ylabel("Latitude (N)")
fig.tight_layout()
fig.savefig("fulldom_check.png", dpi=130)
print("saved fulldom_check.png")
