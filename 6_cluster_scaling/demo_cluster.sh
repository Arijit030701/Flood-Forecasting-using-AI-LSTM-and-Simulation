#!/bin/bash
# LIVE DEMO on the CSE lab machines (run on 172.27.24.10).
#   bash ~/demo_cluster.sh show   ->  MPI on all 8 machines, network test, saved scaling results   (~1 min)
#   bash ~/demo_cluster.sh live   ->  Kerala WRF-Hydro (16 million cells), 2 simulated hours,
#                                     on 16 processes (1 machine) and 128 processes (8 machines)  (~5-8 min)
source ~/wrf_env.sh
mode=${1:-show}

table () {   # best time per process count, with speed-up against 1 process if available
  awk -F, '$4=="ok" { if (!($1 in t) || $3 < t[$1]) { t[$1] = $3; m[$1] = $2 } }
           END { for (p in t) printf "%10d %9d %10.1f %9s\n", p, m[p], t[p], ((1 in t) ? sprintf("%.2f", t[1]/t[p]) : "-") }' "$1" | sort -n
}

if [ "$mode" = show ]; then
  echo "== The hostfile: 8 machines, 16 processes each"
  cat ~/hostfile
  echo; echo "== MPI on all 8 machines at once: 128 processes, each prints its machine name"
  mpirun -np 128 -f ~/hostfile hostname | sort | uniq -c
  echo; echo "== Network test (MPI ping-pong): inside one machine"
  mpirun -np 2 -hosts 172.27.24.10:2 ~/pingpong
  echo; echo "== Network test: between two machines"
  mpirun -np 2 -hosts 172.27.24.10:1,172.27.24.11:1 ~/pingpong
  for d in hydro_scaling hydro_scaling_r10 hydro_scaling_kerala; do
    if [ -f ~/$d/timings.csv ]; then
      echo; echo "== Saved results: $d"
      echo " processes  machines   time(s)  speed-up"
      table ~/$d/timings.csv
    fi
  done
fi

if [ "$mode" = live ]; then
  C=~/hydro_case_kerala_demo
  rm -rf $C && mkdir -p $C
  ln -s ~/hydro_case_kerala/DOMAIN $C/DOMAIN
  ln -s ~/hydro_case_kerala/FORCING $C/FORCING
  cp ~/hydro_case_kerala/namelist.hrldas ~/hydro_case_kerala/hydro.namelist $C/
  sed -i -E 's/^ *(KHOUR|KDAY) = .*/KHOUR = 2/' $C/namelist.hrldas
  grep -E "START_DAY|KHOUR" $C/namelist.hrldas
  echo "== machine load now (should be low, 0-2):"; uptime
  rm -rf ~/hydro_demo
  MPIR_CVAR_CH4_CMA_ENABLE=0 CASE=$C OUT=~/hydro_demo bash ~/scaling_test.sh "16 128"
  echo; echo " processes  machines   time(s)"
  table ~/hydro_demo/timings.csv | awk '{printf "%10s %9s %10s\n", $1, $2, $3}'
fi
