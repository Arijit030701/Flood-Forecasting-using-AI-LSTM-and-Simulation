# Downloads hourly ERA5 weather (the 8 variables WRF-Hydro needs) for a few days over any box.
# Usage (conda OFF):  python3 get_era5_days.py  2018-08-14 2018-08-15  13.5,74.0,7.5,78.5  ~/wrf/kerala_big/era5
#                                               start      end        N,W,S,E              output folder
import sys, os
from datetime import date, timedelta
import cdsapi

d0, d1 = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
area = [float(v) for v in sys.argv[3].split(",")]
out = os.path.expanduser(sys.argv[4]); os.makedirs(out, exist_ok=True)
days = [d0 + timedelta(n) for n in range((d1 - d0).days + 1)]
groups = {
    "instant": ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
                "10m_v_component_of_wind", "surface_pressure"],
    "accum":   ["total_precipitation", "surface_solar_radiation_downwards",
                "surface_thermal_radiation_downwards"],
}
c = cdsapi.Client()
tag = f"{d0:%Y%m%d}-{d1:%Y%m%d}"
for name, variables in groups.items():
    f = os.path.join(out, f"era5_{tag}_{name}.nc")
    if os.path.exists(f) and os.path.getsize(f) > 10_000:
        print("already have", f); continue
    print(f"requesting {tag} {name} ...")
    c.retrieve("reanalysis-era5-single-levels", {
        "product_type": ["reanalysis"], "variable": variables,
        "year": sorted({f"{d.year}" for d in days}), "month": sorted({f"{d.month:02d}" for d in days}),
        "day": sorted({f"{d.day:02d}" for d in days}), "time": [f"{h:02d}:00" for h in range(24)],
        "area": area, "data_format": "netcdf", "download_format": "unarchived",
    }, f)
for f in sorted(os.listdir(out)):
    print(f"  {f}  {os.path.getsize(os.path.join(out, f)) / 1e6:.2f} MB")
