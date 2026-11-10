# Downloads hourly ERA5 weather for the WRF-Hydro Kallada domain (May-Aug 2018), as NetCDF.
# Two files per month: "instant" (temperature, humidity, wind, pressure) and "accum" (rain, sunlight, heat).
# Usage (conda OFF):  python3 get_era5_forcing.py  ~/wrf/kerala_hydro/era5
import sys, os
import cdsapi

out = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/wrf/kerala_hydro/era5")
os.makedirs(out, exist_ok=True)
area = [9.6, 76.3, 8.3, 77.7]                     # N, W, S, E  (a bit bigger than our 1 km domain)
months = ["05", "06", "07", "08"]                 # May = spin-up, Jun-Aug = monsoon + flood
days = [f"{d:02d}" for d in range(1, 32)]
hours = [f"{h:02d}:00" for h in range(24)]
groups = {
    "instant": ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
                "10m_v_component_of_wind", "surface_pressure"],
    "accum":   ["total_precipitation", "surface_solar_radiation_downwards",
                "surface_thermal_radiation_downwards"],
}
c = cdsapi.Client()
for m in months:
    for name, variables in groups.items():
        f = os.path.join(out, f"era5_2018{m}_{name}.nc")
        if os.path.exists(f) and os.path.getsize(f) > 10_000:
            print("already have", f); continue
        print(f"requesting 2018-{m} {name} ...")
        c.retrieve("reanalysis-era5-single-levels", {
            "product_type": ["reanalysis"], "variable": variables,
            "year": ["2018"], "month": [m], "day": days, "time": hours,
            "area": area, "data_format": "netcdf", "download_format": "unarchived",
        }, f)
print("done:")
for f in sorted(os.listdir(out)):
    print(f"  {f}  {os.path.getsize(os.path.join(out, f)) / 1e6:.2f} MB")
