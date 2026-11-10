# Cuts through fake "walls" in the DEM (bridges, dams, road embankments, tall trees) so water can flow
# along the real river, using WhiteboxTools' least-cost breaching. Then reports where it cut.
# Run with conda ON:   python breach_dem.py  dem_kallada.tif  dem_kallada_breached.tif  [search_cells]
import sys, os
import numpy as np
from osgeo import gdal
from whitebox import WhiteboxTools

src = os.path.abspath(sys.argv[1])
out = os.path.abspath(sys.argv[2])
dist = int(sys.argv[3]) if len(sys.argv) > 3 else 200      # longest cut, in DEM cells (200 x 30 m = 6 km)

wbt = WhiteboxTools()
wbt.set_verbose_mode(False)
print(f"breaching {src} (max cut length {dist} cells) ... this can take a few minutes")
ret = wbt.breach_depressions_least_cost(dem=src, output=out, dist=dist, fill=True)
if ret != 0 or not os.path.exists(out):
    sys.exit("WhiteboxTools failed - send me this output")

a = gdal.Open(src)
b = gdal.Open(out)
z0 = a.GetRasterBand(1).ReadAsArray().astype(float)
z1 = b.GetRasterBand(1).ReadAsArray().astype(float)
gt = a.GetGeoTransform()
cut = z0 - z1                 # > 0 where the ground was lowered (breached)
fill = z1 - z0                # > 0 where a pit was filled
print(f"cells lowered: {(cut > 0.5).sum():,}   cells raised: {(fill > 0.5).sum():,}   of {z0.size:,}")
print("deepest cuts (likely bridges/dams/embankments across a river):")
order = np.argsort(cut.ravel())[::-1]
shown = []
for k in order:
    if cut.ravel()[k] < 2 or len(shown) >= 8:
        break
    j, i = divmod(k, cut.shape[1])
    la, lo = gt[3] + (j + 0.5) * gt[5], gt[0] + (i + 0.5) * gt[1]
    if any(abs(la - s[0]) < 0.01 and abs(lo - s[1]) < 0.01 for s in shown):
        continue                                   # skip cells of the same cut
    shown.append((la, lo))
    print(f"   {cut[j, i]:6.1f} m deep at {la:.4f} N {lo:.4f} E")
print("saved", out)
