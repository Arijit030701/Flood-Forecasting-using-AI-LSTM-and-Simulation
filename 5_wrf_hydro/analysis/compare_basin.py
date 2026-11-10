# Compares our model basin (basn_msk in Fulldom_hires.nc) with the official CAMELS-IND catchment outline,
# and shows which land is missing from our basin.
# Usage (with conda on):  python compare_basin.py  Fulldom_hires.nc  catchments.shp  15022  2
#   15022 = CAMELS-IND gauge id,  2 = basin number in our Fulldom (FID of the gauge in gauges.csv)
import sys
import numpy as np
from netCDF4 import Dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path

full, shp, gauge, basin_id = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

def read_rings(shp, gauge):
    """Return the outline rings (lon, lat) of the catchment whose attributes contain the gauge id."""
    try:
        from osgeo import ogr, osr
        ogr.UseExceptions()
        ds = ogr.Open(shp)
        lyr = ds.GetLayer()
        names = [lyr.GetLayerDefn().GetFieldDefn(k).GetName() for k in range(lyr.GetLayerDefn().GetFieldCount())]
        print("shapefile fields:", names)
        src = lyr.GetSpatialRef()
        tr = None
        if src is not None and not src.IsGeographic():        # only convert if the file is not lon/lat
            print("shapefile is projected - converting to lon/lat")
            dst = osr.SpatialReference(); dst.ImportFromEPSG(4326)
            for sr in (src, dst):
                sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            tr = osr.CoordinateTransformation(src, dst)
        else:
            print("shapefile is in lon/lat - no conversion needed")
        for f in lyr:
            vals = [str(f.GetField(n)).split(".")[0] for n in names]
            if gauge in vals:
                geom = f.GetGeometryRef().Clone()
                if tr is not None:
                    geom.Transform(tr)
                polys = [geom.GetGeometryRef(k) for k in range(geom.GetGeometryCount())] \
                        if geom.GetGeometryName() == "MULTIPOLYGON" else [geom]
                return [np.array(p.GetGeometryRef(0).GetPoints())[:, :2] for p in polys]
    except ImportError:
        import shapefile                                  # fallback: pyshp (assumes lon/lat file)
        r = shapefile.Reader(shp)
        names = [fl[0] for fl in r.fields[1:]]
        print("shapefile fields:", names)
        for sr in r.iterShapeRecords():
            if gauge in [str(v).split(".")[0] for v in sr.record]:
                pts, parts = np.array(sr.shape.points), list(sr.shape.parts) + [len(sr.shape.points)]
                return [pts[parts[k]:parts[k + 1]] for k in range(len(parts) - 1)]
    sys.exit(f"gauge {gauge} not found in {shp}")

rings = read_rings(shp, gauge)

nc = Dataset(full)
lat, lon = nc["LATITUDE"][:], nc["LONGITUDE"][:]
topo = np.ma.masked_less(nc["TOPOGRAPHY"][:], -100)
chan = nc["CHANNELGRID"][:]
ours = nc["basn_msk"][:] == basin_id
cell_km2 = (abs(float(nc["x"][1] - nc["x"][0])) / 1000) ** 2

pts = np.column_stack([lon.ravel(), lat.ravel()])
official = np.zeros(pts.shape[0], bool)
for ring in rings:
    official |= Path(ring).contains_points(pts)
official = official.reshape(lat.shape)

a_off, a_our = official.sum() * cell_km2, ours.sum() * cell_km2
miss = official & ~ours
extra = ours & ~official
print(f"official catchment (on our grid): {a_off:7.0f} km2")
print(f"our model basin:                  {a_our:7.0f} km2")
print(f"in both:                          {(official & ours).sum() * cell_km2:7.0f} km2")
print(f"MISSING from ours (official only): {miss.sum() * cell_km2:6.0f} km2")
print(f"extra in ours (not official):      {extra.sum() * cell_km2:6.0f} km2")
if miss.any():
    jj, ii = np.where(miss)
    print(f"missing land lies around {lat[jj, ii].mean():.3f} N {lon[jj, ii].mean():.3f} E "
          f"(lat {lat[jj, ii].min():.2f}-{lat[jj, ii].max():.2f}, lon {lon[jj, ii].min():.2f}-{lon[jj, ii].max():.2f})")

fig, ax = plt.subplots(figsize=(8, 7))
ax.pcolormesh(lon, lat, topo, cmap="Greys_r", shading="auto", alpha=0.8)
ax.pcolormesh(lon, lat, np.ma.masked_where(~miss, miss), cmap="autumn", alpha=0.6, shading="auto")
ax.pcolormesh(lon, lat, np.ma.masked_where(chan < 0, chan + 1), cmap="Blues", vmin=0, vmax=1.2, shading="auto")
ax.contour(lon, lat, ours.astype(int), levels=[0.5], colors="#eda100", linewidths=2)
for ring in rings:
    ax.plot(ring[:, 0], ring[:, 1], color="#e0245e", lw=1.8)
ax.plot([], [], color="#eda100", lw=2, label=f"our basin ({a_our:.0f} km2)")
ax.plot([], [], color="#e0245e", lw=1.8, label=f"official CAMELS-IND ({a_off:.0f} km2)")
ax.fill([], [], color="red", alpha=0.6, label="missing from ours")
ax.legend(loc="lower left")
ax.set_xlim(lon.min(), lon.max()); ax.set_ylim(lat.min(), lat.max())
ax.set_title(f"Gauge {gauge}: our basin vs official catchment")
ax.set_xlabel("Longitude (E)"); ax.set_ylabel("Latitude (N)")
fig.tight_layout()
fig.savefig(f"basin_compare_{gauge}.png", dpi=130)
print(f"saved basin_compare_{gauge}.png")
