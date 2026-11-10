# Step 7: One model on eight machines

Does WRF-Hydro get faster with more cores? We joined 8 identical CSE lab machines (`172.27.24.10–17`,
16 cores each) and ran the same case on 1 to 128 MPI processes. The machines share the home folder over the
network, so one build of WRF-Hydro with MPICH 5.0.2 works on all of them. A hostfile lists the machines with
16 processes each, and `mpirun -np N -f hostfile ./wrf_hydro.exe` starts the run.

## Files

| File | What it does |
|---|---|
| `scaling_test.sh` | Runs the same case on 1, 2, 4 … 128 processes and writes `timings.csv` (processes, machines, seconds, status) |
| `pingpong.c` | Small MPI program that sends a message back and forth to measure network delay and speed |
| `plot_scaling.py` | Plots run time and speed-up from one or more `timings.csv` files; makes `fig_wrfhydro_scaling.png` |
| `demo_cluster.sh` | Live demo: `show` runs MPI on all 8 machines, the ping-pong test and prints saved results (~1 min); `live` runs all of Kerala on 16 and 128 processes (~5–8 min) |
| `fig_wrfhydro_scaling.png` | Run time and speed-up for the three problems |
| `results/timings_*.csv` | Best time for each process count, one file per problem |

## Problems

| Problem | Area | River grid | Simulated time |
|---|---|---|---|
| Kallada, 250 m | 90 × 90 km | 360 × 360 (0.13 million cells) | 5 days |
| Kallada, 100 m | 90 × 90 km | 900 × 900 (0.8 million cells) | 5 days |
| All of Kerala, 100 m | 310 × 520 km | 3100 × 5200 (16 million cells) | 12 hours |

## Results (seconds; speed-up against 1 process in brackets)

| Processes | Machines | Kallada 250 m | Kallada 100 m | All Kerala 100 m |
|---|---|---|---|---|
| 1 | 1 | 104 (1.0) | 591 (1.0) | 5314 (1.0) |
| 2 | 1 | 63 (1.7) | 420 (1.4) | 3527 (1.5) |
| 4 | 1 | 44 (2.4) | 232 (2.6) | 2268 (2.3) |
| 8 | 1 | 33 (3.2) | 202 (2.9) | 1370 (3.9) |
| 16 | 1 | **32 (3.3)** | **193 (3.1)** | 1153 (4.6) |
| 32 | 2 | 257 (0.4) | 450 (1.3) | 751 (7.1) |
| 64 | 4 | 265 (0.4) | 415 (1.4) | 467 (11.4) |
| 128 | 8 | 393 (0.3) | 548 (1.1) | **426 (12.5)** |

Network (`pingpong.c`): an 8-byte message takes 0.5 µs inside one machine and 108 µs between two machines;
large messages move at 18,000 MB/s inside and 116 MB/s between (ordinary 1 Gbit/s Ethernet).

- On one machine, more cores always helped (3.1–4.6× with 16 processes).
- For the small Kallada problems, extra machines made it slower: each process had little work and spent most
  of its time waiting for the network, which WRF-Hydro uses at every 10-second routing step.
- For all of Kerala, the time fell at every step: 12.5× faster on 128 processes, and 8 machines were 2.7×
  faster than one machine.
- More machines pay off only when each process has much more calculation than communication.

## How to run (on 172.27.24.10, inside tmux)

```bash
source ~/wrf_env.sh
mpicc -O2 pingpong.c -o pingpong && mpirun -np 2 -f ~/hostfile ./pingpong     # network test
bash scaling_test.sh "1 2 4 8 16 32 64 128"                                   # writes ~/hydro_scaling/timings.csv
python3 plot_scaling.py results/timings_kallada_250m.csv="Kallada 250 m" \
    results/timings_kallada_100m.csv="Kallada 100 m" results/timings_kerala_100m.csv="All Kerala 100 m"
```

Needs passwordless ssh between the machines, `~/hostfile` (`172.27.24.10:16` … `172.27.24.17:16`) and the
case in `~/hydro_case`. For the Kerala case, MPICH's cross-memory-attach shortcut had to be switched off
(`export MPIR_CVAR_CH4_CMA_ENABLE=0`), because it crashed when splitting the large input.

The CSV files in `results/` were typed from the final table above (best time per process count). The raw
`timings.csv` files from each run are on the lab machines in `~/hydro_scaling/`.
