#!/bin/bash
# CSE SERVER: performance tests for NeuralHydrology and Pangu-Weather on the CPU.
# Run:  nohup bash ~/timing_kit/server_timing.sh > ~/timing.log 2>&1 &
# About 1.5-2 h. Results: ~/timing_results/nh_timing.csv and pangu_timing.csv
K=$HOME/timing_kit; R=$HOME/timing_results; B=$HOME/nh_bench
P=0,2,4,6,8,10,12,14                     # one thread on each of the 8 fast P-cores
mkdir -p $R; cd $K
export PATH=$HOME/.local/bin:$PATH        # nh-run is installed here

echo "start $(date)"
echo "=== free space: remove Kerala WRF input/output (copies are on the laptop) ==="
rm -f ~/wrf/cases/kerala2018/wps/met_em.* ~/wrf/cases/kerala2018/run/wrfout_*
du -sh ~

echo "=== Python packages from ~/server_wheels ==="
python3 -c "import neuralhydrology" 2>/dev/null || {
  python3 -m pip install --user -q --no-index --find-links ~/server_wheels tensorboard netCDF4 onnxruntime
  python3 -m pip install --user -q --no-index --no-deps --find-links ~/server_wheels neuralhydrology; }
python3 -c "import neuralhydrology, onnxruntime, torch; print('packages OK, torch', torch.__version__)" || exit 1

echo "=== NeuralHydrology: 8 fast P-cores ==="
taskset -c $P python3 nh_timing.py run $B $R --device cpu --threads 8 --label server_P8
echo "=== NeuralHydrology: all 32 threads, cores chosen by Linux ==="
python3 nh_timing.py run $B $R --device cpu --label server_all

echo "=== Pangu-Weather: 8 fast P-cores (downloads the 1.1 GB model once) ==="
taskset -c $P python3 pangu_timing.py --device cpu --threads 8 --label server_P8 --steps 3 --out $R
echo "=== Pangu-Weather: all 32 threads ==="
python3 pangu_timing.py --device cpu --label server_all --steps 3 --out $R

du -sh ~
echo "all done $(date)"
cat $R/nh_timing.csv; echo; cat $R/pangu_timing.csv
