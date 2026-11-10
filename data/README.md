# Data (not in git)

Large input files live here on the laptop but are kept out of git by `.gitignore`.

| File | What it is | Used by |
|---|---|---|
| `Rainfall_ind2005_rfp25.grd` | IMD 0.25° daily gridded rain for 2005 (≈25 MB, 135 × 129 grid, 365 days) | `2_wrf/scripts/compare_with_imd.py`, FourCastNet notebook |
| `2018.grd` | IMD 0.25° daily gridded rain for 2018 | `2_wrf/scripts/compare_imd_kerala.py`, `5_wrf_hydro/forcing/make_imd_forcing.py` |

Get IMD files from the IMD Pune website or with the `imdlib` Python package
(`imdlib.get_data('rain', 2005, 2005, fn_format='yearwise')`).
