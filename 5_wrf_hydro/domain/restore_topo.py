# Copies the natural TOPOGRAPHY (no walls) into the walled Fulldom file, so the model's overland flow
# uses real slopes, while the river network keeps the corrected directions.
# Usage (conda OFF):  python3 restore_topo.py  natural/Fulldom_hires.nc  walled/Fulldom_hires.nc
import sys
from netCDF4 import Dataset
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
with Dataset(src) as a, Dataset(dst, "r+") as b:
    t0, t1 = a["TOPOGRAPHY"][:], b["TOPOGRAPHY"][:]
    if t0.shape != t1.shape:
        sys.exit("grids differ - both files must come from the same geogrid and -R")
    print(f"walled topography max {float(t1.max()):.0f} m  ->  natural max {float(t0.max()):.0f} m")
    b["TOPOGRAPHY"][:] = t0
print("TOPOGRAPHY restored in", dst)
