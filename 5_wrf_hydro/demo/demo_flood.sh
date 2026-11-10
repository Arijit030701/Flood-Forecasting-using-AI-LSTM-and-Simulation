#!/bin/bash
# LIVE DEMO (laptop, WSL): WRF-Hydro simulates the August 2018 Kerala flood on the Kallada river.
# It restarts from the model state saved on 10 Aug 2018 by the full IMD run (May-Aug), runs 10 days
# through the flood on 4 cores, and plots the river flow at Pattazhy against the measured flow.
# Usage (conda OFF):   bash ~/wrf/kerala_hydro/demo_flood.sh          (about 3-4 minutes)
K=$HOME/wrf/kerala_hydro
SRC=$K/run_imd                      # the full May-Aug run with IMD rain (has daily restart files)
D=$K/run_demo
R1=$SRC/RESTART.2018081000_DOMAIN1
R2="$SRC/HYDRO_RST.2018-08-10_00:00_DOMAIN1"
for f in "$R1" "$R2" "$K/demo_plot.py" "$K/gauges_snapped.csv"; do
  [ -e "$f" ] || { echo "MISSING: $f"; exit 1; }
done

echo "== 1. Fresh run folder: $D"
rm -rf $D && mkdir -p $D/RESTART && cd $D || exit 1
ln -s $SRC/DOMAIN DOMAIN               # land grid, river grid, groundwater files (same as the full run)
ln -s $K/FORCING_imd FORCING           # hourly weather: ERA5 + IMD rain
cp $SRC/*.TBL $SRC/wrf_hydro.exe $SRC/namelist.hrldas $SRC/hydro.namelist .
cp "$R1" "$R2" RESTART/                # saved soil, groundwater and river state on 10 Aug 00:00 UTC

echo "== 2. Settings: start 10 Aug 2018 from the saved state, run 10 days"
sed -i -E 's|^ *!? *RESTART_FILENAME_REQUESTED.*|RESTART_FILENAME_REQUESTED = "RESTART/RESTART.2018081000_DOMAIN1"|; s/^ *START_MONTH .*/START_MONTH = 08/; s/^ *START_DAY .*/START_DAY   = 10/; s/^ *KDAY = .*/KDAY = 10/; s/^ *RESTART_FREQUENCY_HOURS .*/RESTART_FREQUENCY_HOURS = 1000/' namelist.hrldas
sed -i -E "s|^ *!? *RESTART_FILE .*|RESTART_FILE  = 'RESTART/HYDRO_RST.2018-08-10_00:00_DOMAIN1'|; s/^ *rst_dt .*/rst_dt = 60000/" hydro.namelist
grep -E "START_(YEAR|MONTH|DAY)|KDAY|RESTART_FILENAME" namelist.hrldas
grep -E "^ *RESTART_FILE|DXRT|AGGFACTRT" hydro.namelist

echo "== 3. Running WRF-Hydro with MPI on 4 cores (10 Aug -> 20 Aug 2018) ..."
t0=$(date +%s)
mpirun -np 4 ./wrf_hydro.exe > run.log 2>&1
echo "   model run took $(( $(date +%s) - t0 )) s"
tail -1 diag_hydro.00000
grep -q "finished successfully" diag_hydro.00000 || { echo "RUN FAILED - see: tail -30 $D/run.log"; exit 1; }

echo "== 4. Plot: model vs measured river flow"
/usr/bin/python3 $K/demo_plot.py frxst_pts_out.txt $K/gauges_snapped.csv $K/data FORCING 2018-08-08 2018-08-21
explorer.exe demo_flood.png 2>/dev/null || true
