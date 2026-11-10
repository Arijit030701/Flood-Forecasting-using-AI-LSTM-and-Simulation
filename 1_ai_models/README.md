# Steps 1–2: AI weather models on Indian floods

Two published AI weather models were run, without retraining, on five Indian floods, starting about two days
before each flood. Both notebooks run on a free Google Colab T4 GPU through ECMWF's `ai-models` tool, with
ERA5 as the starting weather.

| Notebook | What it does |
|---|---|
| `fourcastnet.ipynb` | Runs FourCastNet for the 5 floods and compares its rain with the reported gauge rain, IMD's 0.25° grid and ERA5. Also tests starting 1, 2, 3 and 5 days early (Mumbai 2005), 6-hourly timing (Mumbai 2024) and flood size against error. |
| `pangu.ipynb` | Runs Pangu-Weather (it has no rain output) and checks two warning signs at each city: the change in sea-level pressure and in humidity at 850 hPa. Pangu's 24-hour model runs on the CPU and its 6-hour model on the GPU, so it fits in the T4's memory. |

## Main results

| Flood | Observed (mm) | IMD grid (mm) | ERA5 (mm) | FourCastNet (mm) | FourCastNet error |
|---|---|---|---|---|---|
| Mumbai 2005 | 944 | 423 | 74 | 60 | −94% |
| Chennai 2015 | 286 | 329 | 51 | 44 | −85% |
| Idukki 2018 (3 days) | 588 | 456 | 315 | 303 | −49% |
| Delhi 2023 | 153 | 61 | 35 | 11 | −93% |
| Mumbai 2024 (6 h) | 300 | – | 2.5 | 6.3 | −98% |

- FourCastNet saw rain coming but gave far too little: 49–98% too low, whatever the flood size or start day.
- The biggest loss is between IMD and ERA5 on the same grid (31–85% less rain in ERA5). FourCastNet copies ERA5
  closely, so it cannot do better than the data it learned from.
- Pangu-Weather's warning signs did not match flood size (pressure r = −0.45, humidity r = −0.61, 5 events, not significant).
- FourCastNet made a 72-hour global forecast in 41 s on the T4; Pangu-Weather took about 1.5 min.

## How to run

1. Open the notebook in Google Colab and pick a T4 GPU runtime.
2. Run the install cell, then restart the runtime (the notebooks say when).
3. Paste your Copernicus CDS key when asked (needed to download ERA5).
4. For the IMD comparison, upload the yearly IMD files `Rainfall_ind<year>_rfp25.grd` (2005, 2015, 2018, 2023).

Earlier copies of these notebooks were named `multicity_flood_accuracy*.ipynb` (FourCastNet) and
`pangu_multicity_synoptic*.ipynb` (Pangu-Weather).
