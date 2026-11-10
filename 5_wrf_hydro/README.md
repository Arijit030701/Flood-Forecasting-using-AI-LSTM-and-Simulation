# Step 6: A flood model with WRF-Hydro (Kallada river, Kerala 2018)

WRF-Hydro is NCAR's flood model. It moves rain through the soil, over the land and along the rivers.
We set it up from scratch for the Kallada river in Kerala, measured at the Pattazhy gauge (CAMELS-IND 15022),
and ran it through the August 2018 Kerala floods.

## Setup

| Item | Value |
|---|---|
| Build check | NCAR's own test case (a river in New York): KGE 0.60 against USGS flow |
| Catchment | Kallada river at Pattazhy, about 1,200 km² |
| Land grid | 1 km (`geo_em.d01.nc`, Noah-MP land model) |
| River grid | 250 m (`Fulldom_hires.nc`), made from a 30 m elevation map |
| Weather | Hourly ERA5, May–August 2018; a second run with IMD daily rain |
| Observed flow | CAMELS-IND daily flow at Pattazhy (15022); a second gauge, 15007, has no data on 15–18 Aug |

## Results

| | Peak on 16 Aug 2018 (m³/s) | Correlation | NSE |
|---|---|---|---|
| Measured (Pattazhy) | 937 | – | – |
| Model, ERA5 rain | 919 (−2%) | 0.70 | 0.04 |
| Model, IMD rain | 1088 (+16%) | 0.88 | 0.38 |

- The model rose on the right days for every storm of the season.
- IMD rain gave much better timing because it caught storms that ERA5 missed.
- Between storms the model has only about half the measured flow with either rain: the groundwater is
  not tuned yet, and the Thenmala dam, which releases water all monsoon, is not in the model.
- The model's catchment first came out 16% too small. "Walls" along the official outline in the elevation
  map fixed it: 1,224 km² against 1,226 km² for the official outline.

## Scripts, in the order they are used

**1. Choose the gauge** (`domain/`)

| Script | What it does |
|---|---|
| `find_kerala_gauges.py` | Lists CAMELS-IND gauges in Kerala with measured flow in August 2018 |
| `plot_candidates.py` | Plots June–September 2018 flow at a few gauges to check data quality |
| `plot_geo.py` | Shows the 1 km domain (terrain from `geo_em.d01.nc`) with the gauges, to check the basin is inside |

**2. Build the river grid** (`domain/`)

| Script | What it does |
|---|---|
| `breach_dem.py` | Cuts through fake walls in the DEM (bridges, embankments, tall trees) with WhiteboxTools, so water follows the real river |
| `snap_gauges.py` | Moves each gauge onto the nearby channel cell whose upstream area best matches the real catchment area; writes `gauges_snapped.csv` |
| `wall_dem.py` | Raises the DEM along the official catchment boundaries (a gap is left at each gauge), so the river network follows the real catchment |
| `restore_topo.py` | Copies the natural topography back into the walled `Fulldom_hires.nc`, so overland flow uses real slopes while the river network keeps the corrected directions |
| `plot_fulldom.py` | Checks the river channels, basin and gauge points in `Fulldom_hires.nc` |

The river grid itself is made with the WRF-Hydro GIS pre-processing tool from the conditioned DEM.

**3. Make the weather input** (`forcing/`)

| Script | What it does |
|---|---|
| `get_era5_forcing.py` | Downloads hourly ERA5 for the Kallada domain, May–August 2018 |
| `era5_to_ldasin.py` | Turns ERA5 into hourly WRF-Hydro forcing on the 1 km grid (`YYYYMMDDHH.LDASIN_DOMAIN1`: temperature, humidity, wind, pressure, rain, sunlight, heat) |
| `make_imd_forcing.py` | Copy of the forcing with the rain replaced by IMD daily rain, spread over 24 hours with ERA5's own hourly pattern |
| `get_era5_days.py` | Downloads a few days of ERA5 over any box (used for the all-Kerala case in step 7) |

**4. Check the results** (`analysis/`)

| Script | What it does |
|---|---|
| `compare_kerala.py` | Daily model flow against CAMELS-IND flow at the gauges, with rain on top; NSE, KGE, bias, peak |
| `plot_hydro.py` | Plots model flow at each gauge from `frxst_pts_out.txt` or the hourly CHANOBS files |
| `compare_basin.py` | Compares the model's basin with the official CAMELS-IND outline and shows missing land |
| `compare_obs.py` | Model flow against USGS flow for NCAR's New York test case (build check) |

**5. Live demo** (`demo/`)

`demo_flood.sh` restarts WRF-Hydro from the state saved on 10 Aug 2018, runs 10 days through the flood
on 4 cores (about 3–4 minutes) and calls `demo_plot.py` to plot model flow at Pattazhy against the
measured flow and the rain.

## Not stored here

The WRF-Hydro run settings (`namelist.hrldas`, `hydro.namelist`), the domain files (`geo_em.d01.nc`,
`Fulldom_hires.nc`), the forcing and the model output are in the WSL folder `~/wrf/kerala_hydro` on the
laptop. They are large and are rebuilt by the scripts above.

Python packages: numpy, pandas, netCDF4, matplotlib, cdsapi (ERA5 download), GDAL (`osgeo`) and
WhiteboxTools (`whitebox`) for the DEM scripts. The scripts say in their first lines whether to run them with
conda on or off.
