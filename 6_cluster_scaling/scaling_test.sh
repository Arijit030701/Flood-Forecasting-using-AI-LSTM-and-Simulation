#!/bin/bash
# WRF-Hydro strong-scaling test: the SAME Kerala case on 1, 2, 4 ... 128 MPI processes across the lab machines.
# Usage (on 172.27.24.10, inside tmux):   bash scaling_test.sh  "1 2 4 8 16 32 64 96 128"
# Needs: ~/hydro_case (DOMAIN, FORCING, namelists, TBLs), ~/wrf_hydro_nwm_public/build/Run/wrf_hydro.exe,
#        ~/hostfile, passwordless ssh between the machines, and  source ~/wrf_env.sh
source ~/wrf_env.sh
CASE=$HOME/hydro_case
EXE=$HOME/wrf_hydro_nwm_public/build/Run/wrf_hydro.exe
HOSTS=$HOME/hostfile
OUT=$HOME/hydro_scaling
NPS=${1:-"1 2 4 8 16 32 64 96 128"}
mkdir -p $OUT
CSV=$OUT/timings.csv
[ -f $CSV ] || echo "processes,machines,seconds,status" > $CSV
slots=$(awk -F: '{s+=$2} END{print s}' $HOSTS)
echo "hostfile has $slots slots on $(wc -l < $HOSTS) machines; testing: $NPS"

for np in $NPS; do
  if [ $np -gt $slots ]; then echo "skip $np (only $slots slots)"; continue; fi
  d=$OUT/np$np
  rm -rf $d && mkdir -p $d && cd $d
  ln -s $CASE/DOMAIN DOMAIN
  ln -s $CASE/FORCING FORCING
  cp $CASE/namelist.hrldas $CASE/hydro.namelist .
  cp ~/wrf_hydro_nwm_public/build/Run/*.TBL .
  mkdir -p RESTART
  machines=$(awk -F: -v n=$np '{c+=$2; m++; if (c>=n) {print m; exit}}' $HOSTS)
  echo "=== $np processes on $machines machine(s)  $(date +%H:%M:%S)"
  t0=$(date +%s.%N)
  mpirun -np $np -f $HOSTS $EXE > run.log 2>&1
  t1=$(date +%s.%N)
  sec=$(awk -v a=$t0 -v b=$t1 'BEGIN{printf "%.1f", b-a}')
  if tail -1 diag_hydro.00000 2>/dev/null | grep -q "finished successfully"; then st=ok; else st=FAILED; fi
  printf "    %.1f s  (%s)\n" $sec $st
  echo "$np,$machines,$sec,$st" >> $CSV
  rm -f *.LDASOUT_DOMAIN1 *.RTOUT_DOMAIN1 *.CHRTOUT_GRID1         # keep disk use small
done

echo; echo "processes  machines  time(s)  speed-up  efficiency"
awk -F, 'NR>1 && $4=="ok" {if (!t1 && $1==1) t1=$3; n[NR]=$1; m[NR]=$2; t[NR]=$3}
         END {for (i in n) if (t1) printf "%9d %9d %8.1f %9.2f %10.0f%%\n", n[i], m[i], t[i], t1/t[i], 100*t1/t[i]/n[i]}' $CSV | sort -n
