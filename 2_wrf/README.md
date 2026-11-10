# Step 3: Zooming in with WRF

The AI models only work on a 25 km grid, but the Mumbai cloudburst of 26 July 2005 was only 5–10 km wide.
So we ran WRF, a physics weather model, with three nested boxes (27 → 9 → 3 km), using ERA5 as the starting
weather and as the weather at the edges of the outer box every 6 hours.

## Folders

| Folder | What is inside |
|---|---|
| `scripts/` | Install, ERA5 download, WPS and WRF run scripts, rain analysis and IMD comparison (see `scripts/README.txt` for the original kit notes) |
| `namelists/` | `namelist.wps` and `namelist.input` of every run, plus `rsl.error.0000`, the final WRF log (time steps, "SUCCESS COMPLETE WRF") |
| `results/` | Rain tables and maps of every run, compared with the gauge, IMD grid, ERA5 and FourCastNet |
| `timing/` | Run time and peak memory of every run on the laptop and the CSE server |

## The runs

| Run | Folder in `namelists/` | Start (UTC) | Length | Change | Ran on |
|---|---|---|---|---|---|
| A | `mumbai2005` | 25 Jul 2005 00:00 | 60 h | base: WSM6 cloud scheme, new Tiedtke cumulus on 27 and 9 km | laptop, 4 h 25 min |
| B | `mumbai2005_late` | 26 Jul 2005 00:00 | 36 h | starts one day later | laptop 2 h 43 min; server 1 h 33 min |
| C | `mumbai2005_thompson` | 25 Jul 2005 00:00 | 60 h | Thompson cloud scheme + Kain–Fritsch cumulus | laptop, 3 h 47 min |
| D | `mumbai2005_nudge` | 26 Jul 2005 00:00 | 36 h | B + spectral nudging of the 27 km box towards ERA5 | server |
| E | `mumbai2005_nocu9` | 26 Jul 2005 00:00 | 36 h | B with the cumulus scheme switched off on the 9 km box | server |
| Kerala | `kerala2018` | 13 Aug 2018 00:00 | 102 h | same boxes moved to Kerala, run E settings | server, 4 h 50 min |

Domains: d01 27 km, 100 × 100 points (most of India); d02 9 km, 151 × 151 (western India);
d03 3 km, 151 × 151 (Mumbai and the Western Ghats). Other physics: RRTMG radiation, YSU boundary layer,
Noah land surface. Rain is added up over IMD's rain day, 08:30 to 08:30 IST.

## Results

| Folder in `results/` | Contents |
|---|---|
| `results_mumbai2005`, `results_late`, `results_thompson` | Runs A, B, C: rain at the Santacruz gauge, hourly series, 3 km rain map, rain from all sources |
| `results_imd` | Runs A–C on IMD's 25 km grid (first comparison) |
| `results_imd2` | Runs A–E on IMD's 25 km grid: the final table and maps used in the report |
| `results_kerala` | Kerala 2018 run against IMD: scores and 3 km map with terrain |

Final scores on IMD's grid (`results_imd2/wrf_vs_imd_scores.csv`, 165 land boxes; IMD wettest box 732 mm):

| Run | Wettest box (mm) | Bias | Pattern corr. | Peak distance from IMD peak |
|---|---|---|---|---|
| A | 272 | −66% | 0.17 | 136 km |
| B | 272 | −60% | 0.27 | 221 km |
| C | 60 | −94% | 0.29 | 221 km |
| D | 257 | −64% | 0.27 | 221 km |
| E | 236 | −60% | 0.39 | 84 km |

- At 3 km the peak rain was the right size (573 mm in run A), but on the Western Ghats, not over Mumbai.
- Run D changed almost nothing, so the large-scale weather was already right.
- Run E moved the rain to Mumbai's latitude (221 → 84 km) and was the only run to match any boxes above 204.5 mm.
- Kerala 2018: regional rain only 18% low, pattern correlation 0.41, but too much rain on the mountain tops.

## How to run (WSL / Ubuntu)

```bash
bash scripts/install_wrf.sh                                    # once: WRF 4.8.0 + WPS 4.7.0 in ~/wrf
python scripts/download_era5.py 2005-07-25 2005-07-27 ~/wrf/data/era5_mumbai2005
cp -r namelists/mumbai2005 ~/wrf/cases/                        # or any other run folder
bash scripts/run_wps.sh ~/wrf/cases/mumbai2005 ~/wrf/data/era5_mumbai2005
bash scripts/run_wrf.sh ~/wrf/cases/mumbai2005 16              # 16 MPI processes
python scripts/analyse_wrf_rain.py ~/wrf/cases/mumbai2005/run ~/wrf/results_mumbai2005
python scripts/compare_with_imd.py data/Rainfall_ind2005_rfp25.grd ~/wrf/results_imd <run folders...>
```

For the Kerala run, use `namelists/kerala2018/prepare_on_laptop.sh` (ERA5 + WPS on the laptop) and
`run_on_server.sh` (WRF on the server's 8 fast cores), then `scripts/compare_imd_kerala.py`.
On the CSE server, build everything first with `3_performance/server/scripts/install_wrf_server.sh`.

The `wrfout_*` files (2–3 GB per run) are not kept; only the rain tables and figures are.
