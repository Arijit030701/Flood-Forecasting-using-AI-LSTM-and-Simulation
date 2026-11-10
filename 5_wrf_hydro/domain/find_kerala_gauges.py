# Lists CAMELS-IND river gauges in Kerala that have observed flow in August 2018.
# Usage:  python3 find_kerala_gauges.py  <folder where CAMELS-IND was unzipped>
import sys, os, glob
import pandas as pd

root = sys.argv[1]
def find(name):
    f = glob.glob(os.path.join(root, "**", name), recursive=True)
    if not f:
        sys.exit(f"Could not find {name} under {root}. Did the unzip finish? Try: ls -R {root} | head -40")
    print("using", f[0])
    return f[0]

topo_file = find("camels_ind_topo.csv")
flow_file = find("streamflow_observed.csv")
topo = pd.read_csv(topo_file)
# Kerala and the hills on its border
k = topo[topo.cwc_lat.between(8.0, 12.9) & topo.cwc_lon.between(74.8, 77.5)].copy()
k["gauge_id"] = k.gauge_id.astype(int).astype(str)

# number of dams, if the dataset has it
for f in glob.glob(os.path.join(os.path.dirname(topo_file), "*.csv")):
    a = pd.read_csv(f)
    if "num_dams" in a.columns:
        a["gauge_id"] = a.gauge_id.astype(int).astype(str)
        k = k.merge(a[["gauge_id", "num_dams"]], on="gauge_id", how="left")
        break

q = pd.read_csv(flow_file)
q["date"] = pd.to_datetime(q[["year", "month", "day"]])
aug = q[(q.date >= "2018-08-01") & (q.date <= "2018-08-31")]
k["aug2018_days"] = [aug[g].notna().sum() if g in aug else 0 for g in k.gauge_id]
k["aug2018_peak"] = [aug[g].max() if g in aug else None for g in k.gauge_id]
k["peak_date"] = [aug.date[aug[g].idxmax()].strftime("%d %b") if g in aug and aug[g].notna().any() else "-" for g in k.gauge_id]

cols = [c for c in ["gauge_id", "cwc_lat", "cwc_lon", "cwc_area", "num_dams",
                    "aug2018_days", "aug2018_peak", "peak_date"] if c in k.columns]
pd.set_option("display.width", 200)
print(f"{len(k)} gauges in the Kerala area")
print(k[cols].sort_values("cwc_lat").round(3).to_string(index=False))
print("\naug2018_peak is in the dataset's flow units (check the dataset README: mm/day or m3/s)")
