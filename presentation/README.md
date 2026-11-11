# Presentation charts

Charts used in the final presentation (Canva deck "UGP Project Presentation").

| File | Slide | Shows |
|---|---|---|
| `charts/slide05_rain_too_little.png` | The result: far too little rain | Rain from the gauge, IMD grid, ERA5 and FourCastNet for the 5 floods |
| `charts/slide07_wrf_3km_maps.png` | Step 3: Zooming in with WRF | WRF 3 km flood-day rain for runs A, B and C |
| `charts/slide08_imd_vs_wrf_runs.png` | Where the rain fell: real vs WRF | IMD and WRF runs A–E on the same 25 km grid |
| `charts/slide09_server_cores.png` | Step 4: Making it run faster | WRF time on different sets of server cores |
| `charts/slide10_lstm_202_basins.png` | Step 5: From rain to river flow | Test NSE across basins, multi-basin vs single-basin |
| `charts/slide13_eight_machines.png` | Step 7: One model on eight machines | WRF-Hydro run time and speed-up up to 128 processes |
| `charts/overview_kerala_imd_vs_wrf.png` | How a flood forecast is made | IMD observed vs WRF 3 km rain, Kerala, 14–17 Aug 2018 |
| `charts/overview_fourcastnet_globe.png` | The models we worked on | FourCastNet: the whole Earth on one grid (illustration) |
| `charts/overview_pangu_layers.png` | The models we worked on | Pangu-Weather: the surface plus layers of air (illustration) |
| `charts/overview_wrf_nested_domains.png` | The models we worked on | WRF 27/9/3 km boxes from the Mumbai 2005 `namelist.wps` |
| `charts/overview_lstm_202_basins.png` | The models we worked on | The 202 CAMELS-IND basins, coloured by LSTM test NSE |
| `charts/overview_wrfhydro_grids.png` | The models we worked on | WRF-Hydro: 1 km land cells and 250 m river cells (illustration) |
| `charts/map_fourcastnet_5_floods.png` | FourCastNet: what we did | The 5 flood locations; gauge rain vs FourCastNet rain at each, plus the 25 km box at Mumbai |
| `charts/map_pangu_5_floods.png` | Pangu-Weather: what we did | The 5 flood locations; Pangu's pressure and 850 hPa humidity change at each |
| `charts/wrf_grids_27_9_3km.png` | Step 3: Zooming in with WRF | The 27, 9 and 3 km WRF boxes from the Mumbai 2005 `namelist.wps`, and the same 150 km around Mumbai on each grid with a 10 km storm for scale |
| `charts/mumbai2005_wrf_rain_wrong_place.png` | Why was the rain in the wrong place? | IMD flood-day rain around Mumbai (26-27 Jul 2005) and where WRF runs A-E put their heaviest rain (from `2_wrf/results/results_imd2/wrf_vs_imd_scores.csv`) |
| `charts/wrf_speed_laptop_vs_server.png` | Step 4: Making WRF run faster | Same 36-hour WRF forecast (run B): laptop 2 h 43 min vs CSE server 8 fast cores 1 h 33 min (`2_wrf/README.md`) |
| `charts/wrf_speed_which_cores.png` | Step 4: Making WRF run faster | 6-hour WRF forecast time on each set of i9-14900 cores (`2_wrf/timing/benchmark_server.csv`) |
| `charts/wrf_speed_why_slow_cores_hurt.png` | Step 4: Making WRF run faster | Why slow cores slow WRF down: the map is cut into one piece per core, and every core waits for the slowest after each time step (illustration) |
| `charts/river_overlay_india.png` | From rain to floods | Transparent layer for the India satellite image (Sentinel-2 cloudless by EOX, BBOX 67,5.5,92,28.9): the 202 CAMELS-IND gauges of the LSTM, Ambabal (3002) and Pattazhy (15022) ringed |
| `charts/river_overlay_kallada.png` | From rain to floods | Transparent layer for the Kallada satellite image (Sentinel-2 cloudless by EOX, BBOX 76.50,8.68,77.30,9.42): Pattazhy gauge, Thenmala dam, Punalur, Ashtamudi Lake, Kollam |
