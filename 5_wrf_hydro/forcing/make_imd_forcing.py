# Makes a copy of the ERA5 forcing where the rain is replaced by IMD gauge-based daily rain.
# IMD gives one total per day (08:30-08:30 IST = 03-03 UTC, labelled by the END day). Each IMD daily total
# is spread over the 24 hours using ERA5's own hourly pattern in that cell (uniformly if ERA5 had ~no rain).
# Everything else (temperature, wind, sunshine ...) stays ERA5.
# Usage (conda OFF):
#   python3 make_imd_forcing.py  geo_em.d01.nc  Rainfall_ind2018_rfp25.grd  FORCING_era5  FORCING_imd
import sys, os, glob, shutil
import numpy as np
import pandas as pd
from netCDF4 import Dataset

geo, grd, src_dir, out_dir = sys.argv[1:5]
os.makedirs(out_dir, exist_ok=True)

with Dataset(geo) as g:
    XLAT, XLON = g["XLAT_M"][0].astype(float), g["XLONG_M"][0].astype(float)

# ---- IMD 0.25 deg yearly binary file: (days, 129 lat, 135 lon), lat 6.5-38.5, lon 66.5-100, missing -999
imd = np.fromfile(os.path.expanduser(grd), dtype="<f4")
imd = imd.reshape(-1, 129, 135).astype(float)
print(f"IMD file: {imd.shape[0]} days")
glat = 6.5 + 0.25 * np.arange(129)
glon = 66.5 + 0.25 * np.arange(135)
js = np.where((glat >= XLAT.min() - 0.75) & (glat <= XLAT.max() + 0.75))[0]
is_ = np.where((glon >= XLON.min() - 0.75) & (glon <= XLON.max() + 0.75))[0]
sub = imd[:, js][:, :, is_]
sub[sub < -900] = np.nan
lat, lon = glat[js], glon[is_]

def fill_nan(a):
    """Fill sea (NaN) boxes with the mean of land neighbours, so coastal cells can be interpolated."""
    a = a.copy()
    for _ in range(10):
        m = np.isnan(a)
        if not m.any():
            break
        p = np.pad(a, 1, constant_values=np.nan)
        nb = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
        cnt = (~np.isnan(nb)).sum(0)
        mean = np.where(cnt > 0, np.nansum(nb, 0) / np.maximum(cnt, 1), np.nan)
        a[m] = mean[m]
    return np.nan_to_num(a)

# bilinear weights IMD grid -> 1 km grid
jf = np.clip(np.searchsorted(lat, XLAT) - 1, 0, len(lat) - 2); wy = (XLAT - lat[jf]) / 0.25
if_ = np.clip(np.searchsorted(lon, XLON) - 1, 0, len(lon) - 2); wx = (XLON - lon[if_]) / 0.25
def to_1km(f):
    return ((1 - wy) * (1 - wx) * f[jf, if_] + (1 - wy) * wx * f[jf, if_ + 1]
            + wy * (1 - wx) * f[jf + 1, if_] + wy * wx * f[jf + 1, if_ + 1])

# ---- group the hourly ERA5 files by IMD day (hour ending at t belongs to IMD day labelled date(t-4h)+1)
files = sorted(glob.glob(os.path.join(src_dir, "*LDASIN_DOMAIN1")))
times = [pd.Timestamp(os.path.basename(f)[:8] + " " + os.path.basename(f)[8:10] + ":00") for f in files]
label = [(t - pd.Timedelta(hours=4)).floor("D") + pd.Timedelta(days=1) for t in times]
groups = {}
for f, t, d in zip(files, times, label):
    groups.setdefault(d, []).append((t, f))

era_total = imd_total = 0.0
daily = []
for d, items in sorted(groups.items()):
    k = d.dayofyear - 1
    imd_day = to_1km(fill_nan(sub[k])) * len(items) / 24.0       # partial days at the ends: scale down
    era = []
    for t, f in items:
        with Dataset(f) as nc:
            era.append(np.asarray(nc["RAINRATE"][0], dtype=float) * 3600.0)   # mm in that hour
    era = np.array(era)
    era_day = era.sum(0)
    share = np.where(era_day[None] > 1.0, era / np.maximum(era_day[None], 1e-9), 1.0 / len(items))
    new = share * imd_day[None]                                   # mm per hour, IMD daily total
    for (t, f), mm in zip(items, new):
        dst = os.path.join(out_dir, os.path.basename(f))
        shutil.copyfile(f, dst)
        with Dataset(dst, "r+") as nc:
            nc["RAINRATE"][0] = (mm / 3600.0).astype("float32")
    era_total += era_day.mean(); imd_total += imd_day.mean()
    daily.append((d, era_day.mean(), imd_day.mean()))

print(f"wrote {sum(len(v) for v in groups.values())} files to {out_dir}")
df = pd.DataFrame(daily, columns=["imd_day", "era5_mm", "imd_mm"]).set_index("imd_day")
print(f"domain-mean rain, whole period:  ERA5 {era_total:.0f} mm   IMD {imd_total:.0f} mm")
jja = df.loc["2018-06-02":"2018-09-01"]
print(f"domain-mean rain, Jun-Aug:       ERA5 {jja.era5_mm.sum():.0f} mm   IMD {jja.imd_mm.sum():.0f} mm")
fl = df.loc["2018-08-15":"2018-08-18"]
print(f"domain-mean rain, IMD days 15-18 Aug: ERA5 {fl.era5_mm.sum():.0f} mm   IMD {fl.imd_mm.sum():.0f} mm")
print("wettest IMD days (domain mean):")
print(df.sort_values("imd_mm", ascending=False).head(6).round(1).to_string())
