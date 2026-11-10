#!/bin/bash
# LAPTOP (WSL): performance tests for NeuralHydrology and Pangu-Weather on the CPU,
# and preparation of everything the CSE server needs.
# Run inside tmux:   conda activate ddp ;  bash ~/timing_kit/laptop_timing.sh
# Takes about 1-1.5 h. Results: ~/timing_results/nh_timing.csv and pangu_timing.csv
set -e
K=$HOME/timing_kit; R=$HOME/timing_results; W=$HOME/nh_work; B=$HOME/nh_bench
mkdir -p $R $W/raw
cd $K

echo "=== 1/6 Python packages ==="
pip install -q neuralhydrology onnxruntime

echo "=== 2/6 CAMELS-IND data (178 MB) and the same cleaning as in the Colab run ==="
if [ ! -f $W/prep_info.json ]; then
  [ -f $W/raw/camels_ind.zip ] || wget -q --show-progress -O $W/raw/camels_ind.zip \
      "https://zenodo.org/records/14999580/files/CAMELS_IND_Catchments_Streamflow_Sufficient.zip?download=1"
  (cd $W/raw && unzip -q -o camels_ind.zip)
  python -c "import nh_multibasin as nm; nm.prepare('$W/raw', '$W')" | grep -v "it/s"
fi
[ -f $B/bench_info.json ] || python nh_timing.py make-bench $W $B

echo "=== 3/6 NeuralHydrology timing on the laptop CPU (about 30-50 min) ==="
python nh_timing.py run $B $R --device cpu --label laptop

echo "=== 4/6 Pangu-Weather timing on the laptop CPU (downloads the 1.1 GB model once) ==="
python pangu_timing.py --device cpu --label laptop --steps 3 --out $R

echo "=== 5/6 Python packages for the server (it cannot download them itself) ==="
mkdir -p $HOME/server_wheels
PLAT="--platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_27_x86_64 --platform manylinux_2_28_x86_64"
pip download -q --no-deps -d $HOME/server_wheels neuralhydrology
pip download -q --only-binary=:all: --python-version 3.13 $PLAT -d $HOME/server_wheels \
    tensorboard netCDF4 onnxruntime
du -sh $HOME/server_wheels

echo "=== 6/6 Done ==="
cat $R/nh_timing.csv; echo; cat $R/pangu_timing.csv
echo "Next: copy to the server (see the instructions)."
