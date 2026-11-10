# Converts hourly ERA5 (0.25 deg) into WRF-Hydro / Noah-MP hourly forcing files on our 1 km grid:
#   YYYYMMDDHH.LDASIN_DOMAIN1  with T2D, Q2D, U2D, V2D, PSFC, RAINRATE, SWDOWN, LWDOWN
# Usage (conda OFF):  python3 era5_to_ldasin.py  geo_em.d01.nc  era5_folder  FORCING_folder
import sys, os, glob
import numpy as np
from netCDF4 import Dataset, num2date

geo, era_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out_dir, exist_ok=True)

with Dataset(geo) as g:
    XLAT, XLON = g["XLAT_M"][0].astype(float), g["XLONG_M"][0].astype(float)
ny, nx = XLAT.shape

def load(kind):
    """All months of one group, joined in time: dict var -> array (t, lat, lon), plus times, lats, lons."""
    data, times = {}, []
    for f in sorted(glob.glob(os.path.join(era_dir, f"era5_*_{kind}.nc"))):
        with Dataset(f) as nc:
            tname = "valid_time" if "valid_time" in nc.variables else "time"
            tv = nc[tname]
            times += [np.datetime64(t.strftime("%Y-%m-%dT%H:00")) for t in
                      num2date(tv[:], tv.units, getattr(tv, "calendar", "standard"))]
            lat, lon = nc["latitude"][:].astype(float), nc["longitude"][:].astype(float)
            for v in nc.variables:
                if nc[v].ndim == 3:
                    data.setdefault(v, []).append(np.asarray(nc[v][:], dtype="float32"))
    if not times:
        sys.exit(f"no era5_*_{kind}.nc files in {era_dir}")
    return {k: np.concatenate(v) for k, v in data.items()}, np.array(times), lat, lon

inst, t_inst, lat, lon = load("instant")
acc, t_acc, lat2, lon2 = load("accum")
print("instant variables:", list(inst), " accum variables:", list(acc))
print(f"ERA5 grid {len(lat)} x {len(lon)},  {len(t_inst)} hours: {t_inst[0]} to {t_inst[-1]}")

# bilinear weights from the ERA5 lat/lon grid to every 1 km cell (works for ascending or descending lat)
def weights(lat, lon):
    def frac(axis, x):
        if axis[0] > axis[-1]:
            axis, flip = axis[::-1], True
        else:
            flip = False
        i = np.clip(np.searchsorted(axis, x) - 1, 0, len(axis) - 2)
        w = (x - axis[i]) / (axis[i + 1] - axis[i])
        if flip:
            i = len(axis) - 2 - i; w = 1 - w
        return i, np.clip(w, 0, 1)
    j, wy = frac(lat, XLAT)
    i, wx = frac(lon, XLON)
    return j, i, wy, wx

def regrid(field, w):
    j, i, wy, wx = w
    return ((1 - wy) * (1 - wx) * field[j, i] + (1 - wy) * wx * field[j, i + 1]
            + wy * (1 - wx) * field[j + 1, i] + wy * wx * field[j + 1, i + 1])

w_i, w_a = weights(lat, lon), weights(lat2, lon2)
acc_index = {t: k for k, t in enumerate(t_acc)}

def spec_hum(td_k, p_pa):
    td = td_k - 273.15
    e = 6.112 * np.exp(17.67 * td / (td + 243.5)) * 100.0          # vapour pressure, Pa
    return 0.622 * e / (p_pa - 0.378 * e)

written = 0
for k, t in enumerate(t_inst):
    ka = acc_index.get(t)
    if ka is None:
        continue
    T = regrid(inst["t2m"][k], w_i)
    P = regrid(inst["sp"][k], w_i)
    fields = {
        "T2D": (T, "K"),
        "Q2D": (spec_hum(regrid(inst["d2m"][k], w_i), P), "kg kg-1"),
        "U2D": (regrid(inst["u10"][k], w_i), "m s-1"),
        "V2D": (regrid(inst["v10"][k], w_i), "m s-1"),
        "PSFC": (P, "Pa"),
        "RAINRATE": (np.maximum(regrid(acc["tp"][ka], w_a), 0) * 1000.0 / 3600.0, "mm s-1"),
        "SWDOWN": (np.maximum(regrid(acc["ssrd"][ka], w_a), 0) / 3600.0, "W m-2"),
        "LWDOWN": (np.maximum(regrid(acc["strd"][ka], w_a), 0) / 3600.0, "W m-2"),
    }
    stamp = str(t)[:13].replace("-", "").replace("T", "")
    with Dataset(os.path.join(out_dir, f"{stamp}.LDASIN_DOMAIN1"), "w") as nc:
        nc.createDimension("Time", None)
        nc.createDimension("south_north", ny)
        nc.createDimension("west_east", nx)
        for name, (arr, units) in fields.items():
            v = nc.createVariable(name, "f4", ("Time", "south_north", "west_east"))
            v.units = units
            v[0] = arr.astype("float32")
    written += 1
    if written % 500 == 0:
        print(f"  {written} files written (up to {stamp})")

print(f"wrote {written} hourly files to {out_dir}")
r = np.array([acc["tp"][acc_index[t]].mean() for t in t_inst if t in acc_index]) * 1000
print(f"ERA5 area-mean rain over the whole period: {r.sum():.0f} mm")
