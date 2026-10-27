"""Readers that put each source dataset on the GIPL 1 km grid (moved from build_grids.py and build_delta.py).
Variant build.py files combine these. Nothing here sends a server request (sources.* are called with fetch=False).
"""
import warnings
from pathlib import Path

import numpy as np
import pyproj
import rasterio
import xarray as xr
from affine import Affine

from composite_indexing import config as C

from . import grid as G
from . import sources as S

ATLAS14 = C.DATA / "noaa_atlas14/ak/grid/ak100yr24ha_ams.asc"  # hdsc.nws.noaa.gov/pub/hdsc/data/ak/ak100yr24ha_ams.zip
DOT_NC = Path("/import/SNAP/poseidon/CKAN/CKAN_Data/Base/Other/DOT_Precipitation")  # read-only
SUB = 3  # Atlas 14 samples per 1 km cell side (its cells are ~0.9 km N-S, ~0.4 km E-W)


def flam(sel=S.FLAM):
    """ALFRESCO relative flammability (fraction burned per year); nearest cell (same 1 km size; NaN = not burnable)."""
    path = S.flam_path() if sel == S.FLAM else S.flam_hist_path() if sel == S.FLAM_HIST else None
    with rasterio.open(path) as ds:
        return G.to_grid(ds.read(1), ds.transform, G.Resampling.nearest, ds.nodata)


def read_dot(path):
    """dot_precip GeoTIFFs come back transposed: the array is (X, Y) and the header swaps width and height. The bounds
    are right. Plain transpose verified 2026-10-27: 98 % land-mask agreement, Fairbanks = API value (6095.4)."""
    with rasterio.open(path) as ds:
        a, b = ds.read(1).T, ds.bounds
    ny, nx = a.shape
    return a, Affine((b.right - b.left) / nx, 0, b.left, 0, -(b.top - b.bottom) / ny, b.top)


def dot_rasdaman():
    """DOT 24 h, 100-yr pf, 2050-2079, mean of GFDL-CM3 and NCAR-CCSM4 (RCP 8.5), inches; ~481 m averaged to 1 km."""
    models = []
    for paths in S.dot_paths().values():
        acc = np.full(G.SHAPE, np.nan, "float32")
        for p in paths:  # strips overlap by < 1 row: later strip wins
            a, tr = read_dot(p)
            g = G.to_grid(a, tr, G.Resampling.average, -9999)
            acc = np.where(np.isfinite(g), g, acc)
        models.append(acc)
    return np.mean(models, axis=0) / 1000.0  # 1/1000 in -> in


def dot_local(era, duration="24h", interval=100.0):
    """Mean of the two models' pf (inches) from the local SNAP netCDFs, averaged up to 1 km."""
    models = []
    for m in ("GFDL-CM3", "NCAR-CCSM4"):
        with xr.open_dataset(DOT_NC / f"pcpt_{m}_sum_wrf_{duration}_{era}.nc") as ds:
            a = ds.pf.sel(interval=interval).values
            x, y = ds.xc.values, ds.yc.values
        dx, dy = x[1] - x[0], y[1] - y[0]
        tr = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
        models.append(G.to_grid(a, tr, G.Resampling.average, np.nan))
    return np.mean(models, axis=0) / 1000.0


def atlas14():
    """NOAA Atlas 14 Vol. 7 24 h, 100-yr AMS (1/1000 in, NAD83 lon/lat, 0-360 longitudes), inches, averaged over
    SUB x SUB points per 1 km cell."""
    with rasterio.open(ATLAS14) as ds:
        a, t, nd = ds.read(1).astype("float32"), ds.transform, ds.nodata
    a[a == nd] = np.nan
    off = (np.arange(SUB) + 0.5) / SUB * C.GIPL_RES
    xs = C.GIPL_X0 + np.arange(C.GIPL_NX)[:, None] * C.GIPL_RES + off  # (nx, SUB)
    ys = G.TOP - np.arange(C.GIPL_NY)[:, None] * C.GIPL_RES - off      # (ny, SUB)
    X = np.broadcast_to(xs.reshape(1, 1, C.GIPL_NX, SUB), (C.GIPL_NY, SUB, C.GIPL_NX, SUB))
    Y = np.broadcast_to(ys.reshape(C.GIPL_NY, SUB, 1, 1), X.shape)
    lon, lat = pyproj.Transformer.from_crs(C.CRS, 4269, always_xy=True).transform(X.ravel(), Y.ravel())
    col = np.floor((np.mod(lon, 360) - t.c) / t.a).astype(int)
    row = np.floor((lat - t.f) / t.e).astype(int)
    ok = (col >= 0) & (col < a.shape[1]) & (row >= 0) & (row < a.shape[0])
    v = np.full(lon.shape, np.nan, "float32")
    v[ok] = a[row[ok], col[ok]]
    with warnings.catch_warnings():  # all-NaN cells over the ocean
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(v.reshape(C.GIPL_NY, SUB, C.GIPL_NX, SUB), axis=(1, 3)) / 1000.0


def gipl_mean(years, var="magt1m", run="5ModelAvg", scen="rcp45"):
    """Mean of GIPL `var` over climate years (local GeoTIFFs, read via gipl_file_year: labels are 20 years late).
    Stuck cells and their 2 km border masked (D17: keep frozen_class 1 and 2)."""
    acc = np.zeros(G.SHAPE, "float64")
    for y in years:
        f = C.DATA / f"gipl_tif/{var}/gipl_{run}_{scen}_{var}_degC_{C.gipl_file_year(y, run, scen)}.tif"
        with rasterio.open(f) as ds:
            a = ds.read(1).astype("float64")
            a[a == ds.nodata] = np.nan
            acc += a
    out = (acc / len(years)).astype("float32")
    out[~np.isin(G.frozen_class(), (1, 2))] = np.nan
    return out


def pct(new, old):
    with np.errstate(all="ignore"):
        return 100 * (new / old - 1)
