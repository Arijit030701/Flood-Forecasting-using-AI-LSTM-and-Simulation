# Step 4: Making it run faster

How fast each model runs on the laptop, the IIT Kanpur CSE server and a free Colab GPU, and what speeds it up.

| Folder | What is inside |
|---|---|
| `server/scripts/` | Scripts used on the CSE server `csewsrm10` (no admin rights) |
| `server/logs/` | The output log of each server job |
| `ddp/` | Distributed PyTorch (DDP) benchmark for an LSTM river-flow model, laptop and server results |
| `timing/` | NeuralHydrology and Pangu-Weather timing on laptop CPU, server CPU and Colab GPU |

## Server scripts

| Script | What it does | Log |
|---|---|---|
| `install_wrf_server.sh` | Builds tcsh, zlib, HDF5, NetCDF-C/Fortran, MPICH 5.0.2 and WRF 4.8.0 in the home folder, and writes `~/wrf_env.sh` | – |
| `wrf_env.sh` | Sets paths for the libraries above (`source ~/wrf_env.sh`) | – |
| `scale.sh` | Same 6-hour WRF forecast with 32, 24, 16 and 8 processes, cores chosen by Linux | `scaling.log` |
| `pin.sh` | Same forecast pinned with `taskset`: 8 P-cores, 4 P-cores, 8 P-cores × 2 threads, 16 E-cores, 8 P + 16 E | `pin.log` |
| `de.sh`, `fix.sh` | Runs D (nudging) and E (no cumulus at 9 km) on the 8 P-cores, then keeps only the rain fields to fit the 5.4 GB disk limit | `de.log`, `fix.log` |
| `ddp.sh` | DDP benchmark: P-cores only, all cores, and 32 shared threads | `ddp.log` |
| – | Kerala 2018 WRF run (`2_wrf/namelists/kerala2018/run_on_server.sh`) | `kerala.log` |
| – | Run B on the server | `runB.log` |

## Main results

WRF 6-hour forecast on the server (`2_wrf/timing/benchmark_server.csv`):

| Cores | Time (s) |
|---|---|
| 8 P-cores | **947** |
| 8 P-cores, 2 threads each | 1013 |
| 4 P-cores | 1386 |
| 8 P + 16 E-cores | 1514 |
| 16 E-cores | 1734 |

- The 8 fast cores alone were fastest. Adding slow cores made WRF 60% slower, because MPI waits for the slowest process after every step.
- Full 36-hour run B: 2 h 43 min on the laptop, 1 h 33 min on the server's 8 P-cores (1.8× faster).
- DDP (`ddp/`): speed-up grows well up to 8 workers (6.7×); best 8.4× with 24 workers; accuracy unchanged.
- Colab T4 GPU: NeuralHydrology epoch on 10 basins 13.4 s, against 64.9 s on the server and 271.7 s on the laptop (20× faster than the laptop).

## DDP files

| File | Contents |
|---|---|
| `ddp_lstm_benchmark.py` | Trains the same LSTM (hidden 256, 365-day input) with 1, 2, 4 … workers; records epoch time, speed-up and validation NSE |
| `ddp_results_Arijit.csv`, `fig_ddp_scaling_Arijit.png` | Laptop, 16 threads shared by more workers |
| `ddp_results_Arijit_grow.csv`, `fig_ddp_Arijit_grow.png` | Laptop, one core per worker |
| `server/grow_P/`, `server/grow_all/`, `server/fixed32/` | Server: P-cores only, all cores, 32 shared threads |

Run: `python ddp_lstm_benchmark.py --threads-per-worker 1 --workers 1 2 4 8 --samples 1024 --epochs 2 --out results/`
(made-up data of the real size; only the speed matters).

## Timing files

| File | Contents |
|---|---|
| `gpu_timing.ipynb` | Colab notebook: NeuralHydrology and Pangu-Weather timing on the T4 GPU |
| `timing_kit/laptop_timing.sh`, `server_timing.sh` | CPU timing runs on the laptop and the server (~1–2 h each) |
| `timing_kit/nh_timing.py`, `pangu_timing.py` | Time one NeuralHydrology training run / one Pangu-Weather step on any machine |
| `timing_kit/nh_multibasin.py` | Helpers for the 202-basin model (used by `4_neuralhydrology/multibasin`) |
| `ugp_timing/` | Colab GPU results: `nh_timing.csv`, `pangu_timing.csv`, and the NeuralHydrology configs and run logs |
