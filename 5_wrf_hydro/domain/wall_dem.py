# "Walls" the official catchment boundaries into the DEM, so the river network follows the real
# catchment (a standard DEM-conditioning step). A gap is left at each gauge so the river can exit.
# Run with conda ON:
#   python wall_dem.py  dem.tif  catchments.shp  gauges_snapped.csv  dem_walled.tif  [--ids 15022,15007]
import sys, csv, argparse
import numpy as np
from osgeo import gdal, ogr, osr
gdal.UseExceptions(); ogr.UseExceptions()

p = argparse.ArgumentParser()
p.add_argument("dem"); p.add_argument("shp"); p.add_argument("gauges_csv"); p.add_argument("out")
p.add_argument("--ids", default="15022,15007")
p.add_argument("--height", type=float, default=1500.0, help="wall height in m")
p.add_argument("--width", type=int, default=3, help="wall width in DEM cells")
p.add_argument("--gap_km", type=float, default=1.5, help="no wall within this distance of a gauge")
a = p.parse_args()
ids = a.ids.split(",")

ds = gdal.Open(a.dem)
band = ds.GetRasterBand(1)
z = band.ReadAsArray().astype("float32")
gt, ny, nx = ds.GetGeoTransform(), ds.RasterYSize, ds.RasterXSize

# boundaries of the chosen catchments as lines
src = ogr.Open(a.shp)
lyr = src.GetLayer()
names = [lyr.GetLayerDefn().GetFieldDefn(k).GetName() for k in range(lyr.GetLayerDefn().GetFieldCount())]
drv = ogr.GetDriverByName("Memory") or ogr.GetDriverByName("MEM")
mem = drv.CreateDataSource("walls")
srs = osr.SpatialReference(); srs.ImportFromWkt(ds.GetProjection())
ml = mem.CreateLayer("walls", srs, ogr.wkbUnknown)
found = []
for f in lyr:
    vals = [str(f.GetField(n)).split(".")[0] for n in names]
    hit = [i for i in ids if i in vals]
    if hit:
        nf = ogr.Feature(ml.GetLayerDefn())
        nf.SetGeometry(f.GetGeometryRef().Boundary())
        ml.CreateFeature(nf)
        found += hit
print("walling catchments:", found)
if not found:
    sys.exit("none of the gauge ids were found in the shapefile")

mask_ds = gdal.GetDriverByName("MEM").Create("", nx, ny, 1, gdal.GDT_Byte)
mask_ds.SetGeoTransform(gt); mask_ds.SetProjection(ds.GetProjection())
gdal.RasterizeLayer(mask_ds, [1], ml, burn_values=[1], options=["ALL_TOUCHED=TRUE"])
wall = mask_ds.GetRasterBand(1).ReadAsArray().astype(bool)
for _ in range(a.width - 1):                       # make the wall thicker
    w = wall.copy()
    w[1:, :] |= wall[:-1, :]; w[:-1, :] |= wall[1:, :]
    w[:, 1:] |= wall[:, :-1]; w[:, :-1] |= wall[:, 1:]
    wall = w

# leave a gap around each gauge so the river can leave the catchment
lat = gt[3] + (np.arange(ny) + 0.5) * gt[5]
lon = gt[0] + (np.arange(nx) + 0.5) * gt[1]
LON, LAT = np.meshgrid(lon, lat)
with open(a.gauges_csv) as fh:
    for r in csv.DictReader(fh):
        if str(r["Site_No"]) in ids:
            glat, glon = float(r["LAT"]), float(r["LON"])
            d = np.hypot((LAT - glat) * 111.2, (LON - glon) * 111.2 * np.cos(np.radians(glat)))
            wall[d < a.gap_km] = False
            print(f"gap of {a.gap_km} km left at gauge {r['Site_No']} ({glat:.4f} N, {glon:.4f} E)")

nodata = band.GetNoDataValue()
ok = wall if nodata is None else (wall & (z != nodata))
z[ok] += a.height
print(f"raised {int(ok.sum()):,} cells by {a.height:.0f} m")

out = gdal.GetDriverByName("GTiff").Create(a.out, nx, ny, 1, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
out.SetGeoTransform(gt); out.SetProjection(ds.GetProjection())
ob = out.GetRasterBand(1); ob.WriteArray(z)
if nodata is not None:
    ob.SetNoDataValue(nodata)
out.FlushCache(); out = None
print("saved", a.out)
