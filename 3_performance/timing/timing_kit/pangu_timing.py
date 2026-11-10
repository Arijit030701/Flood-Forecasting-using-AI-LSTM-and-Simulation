"""Times Pangu-Weather (6-hour model) on the GPU or the CPU of any machine.

Only the speed is measured: the network gets a random global input of the real size
(5 variables x 13 levels x 721 x 1440 plus 4 surface fields), and each output is fed back in,
like a real forecast. The amount of computation does not depend on the input values.

Usage:
  python pangu_timing.py --device gpu --label colab_t4                 (Colab, T4 GPU)
  python pangu_timing.py --device cpu --label laptop --steps 3         (laptop / server CPU)
  taskset -c 0-15 python pangu_timing.py --device cpu --threads 8 --label server_P8 --steps 3
Output: one line per run appended to pangu_timing.csv (in --out).
"""
import argparse, csv, os, platform, resource, socket, sys, time, urllib.request
import numpy as np

URL = "https://get.ecmwf.int/repository/test-data/ai-models/pangu-weather/pangu_weather_6.onnx"


def cpu_name():
    try:
        return [l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")][0]
    except Exception:
        return platform.processor() or "cpu"


def download(path):
    if os.path.exists(path) and os.path.getsize(path) > 100e6:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    print(f"Downloading the Pangu-Weather 6-hour model (about 1.1 GB) to {path} ...")
    tmp = path + ".part"

    def hook(n, bs, total):
        if total > 0 and n % 200 == 0:
            print(f"  {100 * n * bs / total:5.1f}%", flush=True)
    urllib.request.urlretrieve(URL, tmp, hook)
    os.replace(tmp, path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    p.add_argument("--threads", type=int, default=0, help="CPU threads for onnxruntime (0 = all)")
    p.add_argument("--steps", type=int, default=None, help="timed 6-hour steps (default: 10 GPU, 3 CPU)")
    p.add_argument("--model", default=os.path.expanduser("~/pangu_model/pangu_weather_6.onnx"))
    p.add_argument("--label", default=socket.gethostname())
    p.add_argument("--out", default=".")
    a = p.parse_args()
    steps = a.steps or (10 if a.device == "gpu" else 3)

    import onnxruntime as ort
    download(a.model)
    opts = ort.SessionOptions()
    opts.enable_cpu_mem_arena = False
    opts.enable_mem_pattern = False
    opts.enable_mem_reuse = False
    if a.threads:
        opts.intra_op_num_threads = a.threads
    providers = ([("CUDAExecutionProvider", {"arena_extend_strategy": "kSameAsRequested"}), "CPUExecutionProvider"]
                 if a.device == "gpu" else ["CPUExecutionProvider"])

    t0 = time.perf_counter()
    sess = ort.InferenceSession(a.model, sess_options=opts, providers=providers)
    load_s = time.perf_counter() - t0
    used = sess.get_providers()[0]
    if a.device == "gpu" and used != "CUDAExecutionProvider":
        sys.exit(f"GPU requested but onnxruntime is using {used}. Install onnxruntime-gpu.")
    names = [i.name for i in sess.get_inputs()]
    shapes = [i.shape for i in sess.get_inputs()]
    print(f"{a.label}: {cpu_name()} | onnxruntime {ort.__version__} | {used} | inputs {dict(zip(names, shapes))}")

    rng = np.random.default_rng(0)
    up = rng.standard_normal((5, 13, 721, 1440), dtype=np.float32)
    sf = rng.standard_normal((4, 721, 1440), dtype=np.float32)
    feed = lambda u, s: {"input": u, "input_surface": s}

    t0 = time.perf_counter(); up, sf = sess.run(None, feed(up, sf)); first_s = time.perf_counter() - t0
    print(f"  first step (includes warm-up): {first_s:.1f} s")
    times = []
    for i in range(steps):
        t0 = time.perf_counter()
        up, sf = sess.run(None, feed(up, sf))
        times.append(time.perf_counter() - t0)
        print(f"  step {i + 1}/{steps}: {times[-1]:.2f} s", flush=True)
    mean = float(np.mean(times))
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6   # ru_maxrss is in kB on Linux
    row = dict(label=a.label, host=socket.gethostname(), cpu=cpu_name(), device=a.device, provider=used,
               threads=a.threads or "all", model_load_s=round(load_s, 1), first_step_s=round(first_s, 2),
               mean_step_s=round(mean, 2), steps_timed=steps, forecast_72h_s=round(12 * mean, 1),
               peak_ram_gb=round(peak_gb, 1))
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "pangu_timing.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row)); new and w.writeheader(); w.writerow(row)
    print(f"\n{a.label}: {mean:.2f} s per 6-hour step -> 72-hour forecast (12 steps) about {12 * mean:.0f} s; "
          f"peak RAM {peak_gb:.1f} GB. Saved to {path}")


if __name__ == "__main__":
    main()
