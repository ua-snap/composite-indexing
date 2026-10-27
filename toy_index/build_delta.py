"""Toy index, delta space: change from a baseline to the toy's future period, on the GIPL 1 km grid.

  wildfire   absolute change in relative flammability: 2040-2069 (5modelAvg, RCP 4.5) minus 1980-2008 (MODEL-SPINUP,
             historical); both from Rasdaman alfresco_relative_flammability_30yr (baseline: 1 cached request)
  erosion    percent change in the 24 h, 100-yr storm: DOT 2050-2079 (mean of 2 models, RCP 8.5) vs NOAA Atlas 14
             Vol. 7 (AMS, stations 1867-2011). DOT = Atlas 14 x the WRF model's change since 1979-2005 (Bieniek et
             al. 2022, JAMC 61(2), doi:10.1175/JAMC-D-21-0106.1), so this ratio is the model's projected change; checked
             here: log(DOT/Atlas 14) has under half the < 20 km detail of either map. Also kept: DOT 2020-2049.
  permafrost "progress to thaw" at 1 m: (T_future - T_base) / (0 - T_base) in %, for ground frozen at the start
             (T_base < 0); 100 % = crosses 0 degC. T_base = GIPL 2004-2015 (observed-weather years), T_future = 2040-2069.
             Ground not frozen at the start gets its own flag (no permafrost to lose).
Inputs: <data>/toy_index/grids_1km.npz (build_grids.py) for the future values and the land mask.
Output: <data>/toy_index/grids_delta_1km.npz
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pyproj
import rasterio
import xarray as xr
from affine import Affine
from rasterio.warp import Resampling

from composite_indexing import config as C
import build_grids as G
import fetch_statewide as F

OUT = C.DATA / "toy_index" / "grids_delta_1km.npz"
ATLAS14 = C.DATA / "noaa_atlas14/ak/grid/ak100yr24ha_ams.asc"  # hdsc.nws.noaa.gov/pub/hdsc/data/ak/ak100yr24ha_ams.zip
DOT_NC = Path("/import/SNAP/poseidon/CKAN/CKAN_Data/Base/Other/DOT_Precipitation")  # read-only
BASE_YEARS = range(2004, 2016)  # GIPL climate years run on observed weather, after the 2001-2003 start-up
SUB = 3  # Atlas 14 samples per 1 km cell side (its cells are ~0.9 km N-S, ~0.4 km E-W)


def wildfire_hist():
    with rasterio.open(F.flam_hist_path(fetch=False)) as ds:
        return G.to_grid(ds.read(1), ds.transform, Resampling.nearest, ds.nodata)


def dot_local(era):
    """Mean of the two models' 24 h, 100-yr pf (inches) from the local SNAP netCDFs, averaged up to 1 km."""
    models = []
    for m in ("GFDL-CM3", "NCAR-CCSM4"):
        with xr.open_dataset(DOT_NC / f"pcpt_{m}_sum_wrf_24h_{era}.nc") as ds:
            a = ds.pf.sel(interval=100.0).values
            x, y = ds.xc.values, ds.yc.values
        dx, dy = x[1] - x[0], y[1] - y[0]
        tr = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
        models.append(G.to_grid(a, tr, Resampling.average, np.nan))
    return np.mean(models, axis=0) / 1000.0


def atlas14():
    """NOAA Atlas 14 (1/1000 in, NAD83 lon/lat, 0-360 longitudes) averaged over SUB x SUB points per 1 km cell."""
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
    with np.errstate(all="ignore"):
        return np.nanmean(v.reshape(C.GIPL_NY, SUB, C.GIPL_NX, SUB), axis=(1, 3)) / 1000.0


def permafrost_base():
    acc = np.zeros(G.SHAPE, "float64")
    for y in BASE_YEARS:
        with rasterio.open(C.DATA / f"gipl_tif/magt1m/gipl_5ModelAvg_rcp45_magt1m_degC_{C.gipl_file_year(y)}.tif") as ds:
            a = ds.read(1).astype("float64")
            a[a == ds.nodata] = np.nan
            acc += a
    return (acc / len(BASE_YEARS)).astype("float32")


def pct(new, old):
    with np.errstate(all="ignore"):
        return 100 * (new / old - 1)


def main():
    g = np.load(C.DATA / "toy_index" / "grids_1km.npz")
    land = g["land"]
    out = {}
    try:
        out["wildfire_base"] = wildfire_hist()
        out["wildfire"] = g["wildfire"] - out["wildfire_base"]
    except FileNotFoundError as e:
        print(f"wildfire skipped: {e}")
    out["erosion_base"] = atlas14()
    out["erosion_dot2020"] = dot_local("2020-2049")
    out["erosion"] = pct(g["erosion"], out["erosion_base"])
    out["erosion_vs_dot2020"] = pct(g["erosion"], out["erosion_dot2020"])
    out["dot2020_vs_atlas14"] = pct(out["erosion_dot2020"], out["erosion_base"])
    tb = permafrost_base()
    tb[~np.isfinite(g["permafrost"])] = np.nan  # same stuck-cell mask as the future grid
    out["permafrost_base"] = tb
    with np.errstate(all="ignore"):
        out["permafrost"] = np.where(tb < 0, 100 * (g["permafrost"] - tb) / -tb, np.nan).astype("float32")
    out["permafrost_unfrozen_start"] = land & (tb >= 0)
    for k, a in out.items():
        if a.dtype == bool:
            print(f"{k:22s} share of land {a[land].mean():.3f}")
            continue
        a[~land] = np.nan
        q = np.nanquantile(a, [0, .1, .25, .5, .75, .9, 1])
        print(f"{k:22s} valid={np.isfinite(a)[land].mean():.3f} q(0,10,25,50,75,90,100)={np.round(q, 4)}")
    np.savez_compressed(OUT, **out)
    r, c = rasterio.transform.rowcol(G.GRID, *pyproj.Transformer.from_crs(4326, C.CRS, always_xy=True)
                                     .transform(-147.643, 64.828))
    print("Fort Wainwright:", {k: round(float(a[r, c]), 4) for k, a in out.items()})
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
