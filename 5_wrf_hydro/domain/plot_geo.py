# Shows the WRF-Hydro domain (terrain from geo_em) with the river gauges, to check the basin is inside.
# Usage:  python3 plot_geo.py  geo_em.d01.nc
import sys
import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

nc = Dataset(sys.argv[1])
lat, lon = nc["XLAT_M"][0], nc["XLONG_M"][0]
hgt = nc["HGT_M"][0]
print(f"grid {hgt.shape[1]} x {hgt.shape[0]} points, DX = {nc.DX:.0f} m")
print(f"lat {lat.min():.2f} to {lat.max():.2f} N,  lon {lon.min():.2f} to {lon.max():.2f} E")
print(f"height {hgt.min():.0f} to {hgt.max():.0f} m")

gauges = {"15022 Kallada (Pattazhy)": (9.0728, 76.7611), "15007": (8.715, 76.850)}
fig, ax = plt.subplots(figsize=(7, 6.5))
m = ax.pcolormesh(lon, lat, hgt, cmap="terrain", shading="auto")
fig.colorbar(m, label="Height (m)")
for name, (la, lo) in gauges.items():
    ax.plot(lo, la, "o", color="red", ms=8, mec="white")
    ax.annotate(name, (lo, la), xytext=(5, 5), textcoords="offset points", color="white",
                fontsize=9, weight="bold")
ax.set_xlabel("Longitude (E)")
ax.set_ylabel("Latitude (N)")
ax.set_title("WRF-Hydro domain: terrain and river gauges")
fig.tight_layout()
fig.savefig("domain_check.png", dpi=120)
print("saved domain_check.png")
