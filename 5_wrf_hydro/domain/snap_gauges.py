# Moves each gauge onto the river channel cell nearby whose upstream area best matches the real
# catchment area, and writes gauges_snapped.csv for the GIS tool.
# Usage:  python3 snap_gauges.py  Fulldom_hires.nc  gauges.csv  15007:540  15022:1210   [radius_cells]
import sys
import numpy as np
import pandas as pd
from netCDF4 import Dataset

nc = Dataset(sys.argv[1])
g = pd.read_csv(sys.argv[2])
target = {int(a.split(":")[0]): float(a.split(":")[1]) for a in sys.argv[3:] if ":" in a}
radius = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 6

lat, lon = nc["LATITUDE"][:], nc["LONGITUDE"][:]
chan, acc = nc["CHANNELGRID"][:], nc["FLOWACC"][:].astype(float)
x = nc["x"][:]
cell_km2 = (abs(float(x[1] - x[0])) / 1000) ** 2
print(f"routing cell = {abs(float(x[1]-x[0])):.0f} m  ->  {cell_km2:.4f} km2 per cell")

rows = []
for _, r in g.iterrows():
    site = int(r.Site_No)
    d2 = (lat - r.LAT) ** 2 + ((lon - r.LON) * np.cos(np.radians(r.LAT))) ** 2
    j0, i0 = np.unravel_index(np.argmin(d2), d2.shape)
    want = target.get(site, np.nan)
    print(f"\nGauge {site} (FID {r.FID}): nearest cell area {acc[j0, i0] * cell_km2:.0f} km2, "
          f"on channel: {chan[j0, i0] >= 0}, real catchment {want:.0f} km2")
    cands = []
    for j in range(max(j0 - radius, 0), min(j0 + radius + 1, acc.shape[0])):
        for i in range(max(i0 - radius, 0), min(i0 + radius + 1, acc.shape[1])):
            if chan[j, i] < 0:
                continue
            area = acc[j, i] * cell_km2
            dist_km = np.hypot(j - j0, i - i0) * np.sqrt(cell_km2)
            score = abs(area - want) / want + 0.05 * dist_km      # area match first, then distance
            cands.append((score, area, dist_km, j, i))
    cands.sort()
    print("  best nearby channel cells:   area (km2)   distance (km)")
    for c in cands[:5]:
        print(f"                                {c[1]:8.0f}      {c[2]:6.2f}")
    _, area, dist, j, i = cands[0]
    print(f"  -> using cell at {lat[j, i]:.5f} N {lon[j, i]:.5f} E: area {area:.0f} km2 "
          f"({100 * (area / want - 1):+.0f}% vs real), moved {dist:.2f} km")
    rows.append(dict(FID=r.FID, LON=round(float(lon[j, i]), 6), LAT=round(float(lat[j, i]), 6),
                     STATION=r.STATION, Site_No=site))
pd.DataFrame(rows).to_csv("gauges_snapped.csv", index=False)
print("\nsaved gauges_snapped.csv")
