"""Toy index: put the three raw datasets on the GIPL 1 km grid (EPSG:3338, 1941 x 2471).

  wildfire   ALFRESCO relative flammability, 2040-2069, 5modelAvg, RCP 4.5 (fraction burned per year); nearest
             (same 1 km cell size; raw pixels, NaN = not burnable)
  erosion    DOT 24 h, 100-yr precipitation depth, 2050-2079, mean of GFDL-CM3 and NCAR-CCSM4 (RCP 8.5), inches;
             ~481 m averaged up to 1 km
  permafrost GIPL magt1m, 5ModelAvg RCP 4.5, mean of climate years 2040-2069 (local GeoTIFFs, gipl_file_year);
             stuck cells and their 2 km border masked (D17: frozen_class 3, 4)
All three are cut to the GIPL land mask. Output: <data>/toy_index/grids_1km.npz + one GeoTIFF per index.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
from affine import Affine
from rasterio.warp import Resampling, reproject

from composite_indexing import config as C
import fetch_statewide as F

OUT = C.DATA / "toy_index"
TOP = C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES
GRID = Affine(C.GIPL_RES, 0, C.GIPL_X0, 0, -C.GIPL_RES, TOP)
SHAPE = (C.GIPL_NY, C.GIPL_NX)
YEARS = range(2040, 2070)


def to_grid(src, transform, resampling, nodata):
    dst = np.full(SHAPE, np.nan, "float32")
    reproject(src.astype("float32"), dst, src_transform=transform, src_crs=C.CRS, src_nodata=nodata,
              dst_transform=GRID, dst_crs=C.CRS, dst_nodata=np.nan, resampling=resampling)
    return dst


def wildfire():
    with rasterio.open(F.flam_path()) as ds:
        return to_grid(ds.read(1), ds.transform, Resampling.nearest, ds.nodata)


def read_dot(path):
    """dot_precip GeoTIFFs come back transposed: the array is (X, Y) and the header swaps width and height. The bounds
    are right. Plain transpose verified 2026-10-27: 98 % land-mask agreement, Fairbanks = API value (6095.4)."""
    with rasterio.open(path) as ds:
        a, b = ds.read(1).T, ds.bounds
    ny, nx = a.shape
    return a, Affine((b.right - b.left) / nx, 0, b.left, 0, -(b.top - b.bottom) / ny, b.top)


def erosion():
    models = []
    for paths in F.dot_paths().values():
        strips = [read_dot(p) for p in paths]
        acc = np.full(SHAPE, np.nan, "float32")
        for a, tr in strips:  # strips overlap by < 1 row: later strip wins
            g = to_grid(a, tr, Resampling.average, -9999)
            acc = np.where(np.isfinite(g), g, acc)
        models.append(acc)
    return np.mean(models, axis=0) / 1000.0  # 1/1000 in -> in


def permafrost():
    acc = np.zeros(SHAPE, "float64")
    for y in YEARS:
        with rasterio.open(C.DATA / f"gipl_tif/magt1m/gipl_5ModelAvg_rcp45_magt1m_degC_{C.gipl_file_year(y)}.tif") as ds:
            a = ds.read(1).astype("float64")
            a[a == ds.nodata] = np.nan
            acc += a
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as ds:
        cls = ds.read(1)
    out = (acc / len(YEARS)).astype("float32")
    out[~np.isin(cls, (1, 2))] = np.nan
    return out, cls > 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pf, land = permafrost()
    grids = dict(wildfire=wildfire(), erosion=erosion(), permafrost=pf)
    for k, a in grids.items():
        a[~land] = np.nan
        q = np.nanquantile(a, [0, .1, .25, .5, .75, .9, 1])
        print(f"{k:10s} valid={np.isfinite(a)[land].mean():.3f} quantiles(0,10,25,50,75,90,100)={np.round(q, 4)}")
        with rasterio.open(OUT / f"{k}_1km.tif", "w", driver="GTiff", height=SHAPE[0], width=SHAPE[1], count=1,
                           dtype="float32", crs=C.CRS, transform=GRID, nodata=np.nan, compress="deflate") as ds:
            ds.write(a, 1)
    np.savez_compressed(OUT / "grids_1km.npz", land=land, transform=np.array(GRID)[:6], **grids)
    r, c = rasterio.transform.rowcol(GRID, 297_699, 1_667_062)
    print("Fairbanks cell:", {k: float(a[r, c]) for k, a in grids.items()})


if __name__ == "__main__":
    main()
