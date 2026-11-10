# Forecasting Indian Floods: from Rain to River

Undergraduate Project (CS496), IIT Kanpur, semester I 2026-27
**Arijit Vishwakarma**· Supervisor: **Prof. Preeti Malakar** (CSE)

This project asks whether today's weather and flood models can warn us about big Indian floods, and how fast
they run on the computers we have. It is one story in seven steps: each step starts from what the step before
it found.

| Step | Question | Folder | Main result |
|---|---|---|---|
| 1 | Can AI weather models (FourCastNet, Pangu-Weather) forecast flood rain? | [`1_ai_models/`](1_ai_models) | FourCastNet gave 49–98% too little rain in all 5 floods. Pangu-Weather has no rain output, and its warning signs did not match flood size. |
| 2 | Where is the rain lost? | [`1_ai_models/`](1_ai_models) | Mumbai 2005: gauge 944 mm → IMD grid 423 mm → ERA5 74 mm → FourCastNet 60 mm. Most rain is already missing in ERA5, the training data. |
| 3 | Does a finer physics model help? | [`2_wrf/`](2_wrf) | WRF at 3 km gave rain of the right size (573 mm) but 100–240 km away on the Western Ghats. Switching off the cumulus scheme on the 9 km box moved it from 221 to 84 km. |
| 4 | Can we run it faster? | [`3_performance/`](3_performance) | CSE server, 8 fast cores only: 1.8× faster than the laptop. PyTorch DDP: LSTM training up to 8.4× faster. Colab T4 GPU: 20× faster than the laptop. |
| 5 | Can we predict river flow? | [`4_neuralhydrology/`](4_neuralhydrology) | One LSTM for 202 CAMELS-IND basins: median NSE 0.39 (wet basins 0.61), better than one model per basin (0.32 vs 0.21). |
| 6 | Can a flood model catch a real flood? | [`5_wrf_hydro/`](5_wrf_hydro) | WRF-Hydro on the Kallada river (Kerala): 2018 flood peak 919 m³/s with ERA5 rain against 937 m³/s measured at Pattazhy. |
| 7 | Do more machines make it faster? | [`6_cluster_scaling/`](6_cluster_scaling) | On 8 lab machines: 12.5× faster for all of Kerala (16 million cells), but slower for a small river because the network is slow. |

The full write-up is in [`report/report.pdf`](report/report.pdf), and the slide charts are in [`presentation/charts/`](presentation/charts).

## Folder layout

```
Arijit_UGP_SEM5/
├── report/                 report PDF and the LaTeX section on the 8-machine test
├── presentation/charts/    charts used in the final presentation
├── 1_ai_models/            FourCastNet and Pangu-Weather notebooks (steps 1–2)
├── 2_wrf/                  WRF downscaling: scripts, settings of every run, results, timing (step 3)
├── 3_performance/          CSE server builds and logs, DDP benchmark, GPU/CPU timing (step 4)
├── 4_neuralhydrology/      LSTM river-flow models with NeuralHydrology (step 5)
├── 5_wrf_hydro/            WRF-Hydro flood model for the Kallada river, Kerala 2018 (step 6)
├── 6_cluster_scaling/      WRF-Hydro on 8 lab machines with MPI (step 7)
└── data/                   large input data, kept out of git (see data/README.md)
```

Each folder has its own README with what every file does and how to run it.

## Flood events

| Event | AI forecast start | Observed rain | Used in |
|---|---|---|---|
| Mumbai 2005 | 24 Jul 2005 | 944 mm in 24 h, flood day 26 July (IMD Santacruz) | AI models, WRF runs A–E |
| Chennai 2015 | 29 Nov 2015 | 286 mm in 24 h (city average) | AI models |
| Idukki / Kerala 2018 | 13 Aug 2018 | 588 mm over 15–17 August | AI models, WRF Kerala run, WRF-Hydro, scaling test |
| Delhi 2023 | 7 Jul 2023 | 153 mm in 24 h (IMD Safdarjung) | AI models |
| Mumbai 2024 | 6 Jul 2024 | 300 mm in 6 h (IMD red alert, 01:00–07:00 IST) | AI models |

The main "truth" for rain is IMD's gauge-based 0.25° (≈25 km) gridded rainfall, which is on the same grid
as the AI models and ERA5. For river flow it is the measured daily flow in CAMELS-IND.

## Machines

| Machine | CPU | Used for |
|---|---|---|
| Laptop (WSL2) | Intel Core Ultra 9 185H, 6 fast + 10 slower cores, 24 GB | WRF runs A–C, WRF-Hydro, timing |
| CSE server `csewsrm10` | Intel Core i9-14900, 8 fast + 16 slower cores, 62 GB | WRF runs D, E and Kerala, DDP, timing |
| 8 CSE lab machines `172.27.24.10–17` | 16 cores each, 1 Gbit Ethernet | WRF-Hydro scaling (up to 128 MPI processes) |
| Google Colab | NVIDIA T4 GPU | FourCastNet, Pangu-Weather, NeuralHydrology training |

## Data not stored here

These are too large for git. Each README says where its scripts expect them.

| Data | Where to get it |
|---|---|
| ERA5 (start and boundary weather, WRF-Hydro forcing) | Copernicus Climate Data Store (CDS), with `cdsapi` and a `~/.cdsapirc` key |
| IMD 0.25° daily gridded rain (`Rainfall_ind<year>_rfp25.grd`) | IMD Pune website, or the `imdlib` Python package |
| CAMELS-IND (river flow, weather and catchment attributes) | Zenodo record 14999580 |
| WPS static terrain data | UCAR (WRF users' page) |
| WRF output (`wrfout_*`), WRF-Hydro output and forcing | made by the scripts; only rain and summary tables are kept here |

## Tools

FourCastNet and Pangu-Weather through ECMWF `ai-models`; WRF 4.8.0 and WPS 4.7.0; WRF-Hydro (NCAR,
`wrf_hydro_nwm_public`); NeuralHydrology (PyTorch); MPICH 5.0.2 built without admin rights; Python with
numpy, pandas, netCDF4, matplotlib, imdlib, GDAL and WhiteboxTools for the DEM work.
