"""The common grid of every toy index variant: the GIPL 1 km grid (EPSG:3338, 1941 x 2471)."""
import numpy as np
import rasterio
from affine import Affine
from rasterio.warp import Resampling, reproject  # noqa: F401 (Resampling re-exported for readers)

from composite_indexing import config as C

TOP = C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES
GRID = Affine(C.GIPL_RES, 0, C.GIPL_X0, 0, -C.GIPL_RES, TOP)
SHAPE = (C.GIPL_NY, C.GIPL_NX)
FROZEN_CLASS = C.DATA / "results/gipl_artifact/statewide_frozen_class.tif"  # D17: 0 nodata, 1 no PF, 2 PF good,
                                                                             # 3 near stuck, 4 stuck


def to_grid(src, transform, resampling, nodata, crs=C.CRS):
    dst = np.full(SHAPE, np.nan, "float32")
    reproject(src.astype("float32"), dst, src_transform=transform, src_crs=crs, src_nodata=nodata,
              dst_transform=GRID, dst_crs=C.CRS, dst_nodata=np.nan, resampling=resampling)
    return dst


def frozen_class():
    with rasterio.open(FROZEN_CLASS) as ds:
        return ds.read(1)


def land():
    """Alaska land = the GIPL land mask (frozen_class > 0). Every variant is cut to it."""
    return frozen_class() > 0
