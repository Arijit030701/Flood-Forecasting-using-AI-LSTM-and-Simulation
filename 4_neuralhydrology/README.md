# Step 5: From rain to river flow (LSTM)

Floods happen in rivers, so this step predicts daily river flow with an LSTM, using the NeuralHydrology
library (PyTorch). The LSTM reads the weather of the previous 365 days for a catchment and predicts the flow
on the last day. Scores: NSE (1 = perfect, 0 = no better than the average flow) and KGE.

| Folder | What is inside |
|---|---|
| `tutorial_camels_us/` | `Introduction.ipynb`, NeuralHydrology's own tutorial on one CAMELS US basin, used to check the setup (NSE 0.776, reference 0.777) |
| `single_basin/` | `NeuralHydrology.ipynb`: first models for one Indian basin (CAMELS-IND 3002), with NCEP FNL and CAMELS-IND weather |
| `multibasin/` | `camels_ind_multibasin.ipynb`: one model for all 202 usable CAMELS-IND basins, and its `results/` |
| `sample_data/` | `3002.csv` (daily data for basin 3002) and `attributes.csv` (catchment attributes) from CAMELS-IND |
| `docs/` | `NeuralHydrology_Project_Report.docx`, the early report on the single-basin work |

## Results

| Model | Median NSE | Median KGE | NSE > 0.5 |
|---|---|---|---|
| Multi-basin, all 202 basins | 0.39 | 0.50 | 42% |
| Multi-basin, the 11 comparison basins | 0.32 | 0.30 | 45% |
| Single-basin, the same 11 basins | 0.21 | 0.24 | 27% |

- The first single-basin model scored NSE ≈ 0 because of wrong flow values (the same impossible
  946.47 mm/day on five days in September 2018).
- After cleaning (negative flows, repeated extreme values, flow far above the past week's rain: 527 values
  in 40 basins), one model for all basins beat one model per basin.
- Wet basins work well (median NSE 0.61 in the wettest third); dry basins do not (about 0).
- Training: CudaLSTM, 128 hidden units, NSE loss, 30 epochs; train 1981–2004, validate 2005–2009, test
  2010–2020; 169 min on a Colab T4 GPU.

`multibasin/results/` holds `summary.csv` (table above), `test_scores_per_basin.csv`, `qc_report.csv`
(what was removed in cleaning), `prep_info.json`, `training_minutes.json`, `attributes.csv` and the two
figures (`fig_nh_nse_cdf.png`, `fig_nh_3002_hydrograph.png`).

## How to run

Open `multibasin/camels_ind_multibasin.ipynb` in Colab with a T4 GPU. It needs CAMELS-IND (Zenodo record
14999580, version 2.2) and the helpers in `3_performance/timing/timing_kit/nh_multibasin.py`.
The single-basin notebook also needs an NSF NCAR GDEX account for the NCEP FNL data (dataset d083002).
