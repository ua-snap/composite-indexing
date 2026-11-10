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

ATLAS14_DIR = C.DATA / "noaa_atlas14/ak/grid"  # hdsc.nws.noaa.gov/pub/hdsc/data/ak/<name>.zip, unzipped
# DOT duration label -> Atlas 14 file duration code (SNAP's pipeline multiplies the annual maximum series, *_ams)
ATLAS14_DUR = {"60m": "60ma", "2h": "02ha", "3h": "03ha", "6h": "06ha", "12h": "12ha", "24h": "24ha", "2d": "48ha",
               "3d": "03da", "4d": "04da", "7d": "07da", "10d": "10da", "20d": "20da", "30d": "30da", "45d": "45da",
               "60d": "60da"}
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
    return np.mean(dot_models(era, duration, interval), axis=0)


def dot_models(era, duration="24h", interval=100.0):
    """[GFDL-CM3, NCAR-CCSM4] pf (inches) from the local SNAP netCDFs, each averaged up to 1 km."""
    models = []
    for m in ("GFDL-CM3", "NCAR-CCSM4"):
        with xr.open_dataset(DOT_NC / f"pcpt_{m}_sum_wrf_{duration}_{era}.nc") as ds:
            a = ds.pf.sel(interval=interval).values
            x, y = ds.xc.values, ds.yc.values
        dx, dy = x[1] - x[0], y[1] - y[0]
        tr = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
        models.append(G.to_grid(a, tr, G.Resampling.average, np.nan) / 1000.0)
    return models


def atlas14(duration="24h", interval=100):
    """NOAA Atlas 14 Vol. 7 annual-maximum-series depth (1/1000 in, NAD83 lon/lat, 0-360 longitudes) for a DOT
    duration label and return interval, inches, averaged over SUB x SUB points per 1 km cell."""
    with rasterio.open(ATLAS14_DIR / f"ak{int(interval)}yr{ATLAS14_DUR[duration]}_ams.asc") as ds:
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


def esa_gate():
    """ESA CCI Permafrost v5 permafrost zone: PFR 2023 > 0 (the PTI gate, D12/D26). Cells with no ESA value (85 % in
    the South, where GIPL also shows no permafrost) count as outside. Every permafrost variant uses it (2026-11-09)."""
    with xr.open_dataset(C.DATA / "features/features_1km.nc") as ds:
        return ds.pfr_2023.values > 0


def esa_gst_today():
    """ESA CCI ground surface temperature, mean of 2014-2023 (degC), on the GIPL grid."""
    with xr.open_dataset(C.DATA / "features/features_1km.nc") as ds:
        return ds.esa_gst_recent.values


def dot_change_models(duration="24h", interval=100, era="2050-2079"):
    """[GFDL-CM3, NCAR-CCSM4] % change from NOAA Atlas 14 (annual maximum series) to `era`."""
    at = atlas14(duration, interval)
    return [pct(m, at) for m in dot_models(era, duration, float(interval))]


def pct(new, old):
    with np.errstate(all="ignore"):
        return 100 * (new / old - 1)


FWI_SUMMARY = C.DATA / "fwi/fwi_alaska_2040-2069_ssp585.nc"  # scripts/01_data/summarize_fwi.py
FWI_HIGH = ("High", "VHigh", "Ext")  # Alaska fire danger ratings counted as "high or worse" (FWI >= 18)


def fwi_models(stat="season_mean"):
    """Per-model FWI statistic for 2040-2069 (SSP5-8.5) on the native 0.25 deg grid:
    (values[model, lat, lon], transform, model names). stat:
      season_mean  mean daily FWI, April-October (months weighted by their days)
      peak_week    highest 7-day centred rolling mean of the 2040-2069 mean seasonal curve (SNAP API
                   op=7_day_rolling_average "mean", then its highest day; only full windows inside Apr-Oct)
      high_days    mean days per June-August with FWI >= 18 (High, Very High or Extreme fire danger; API
                   op=summer_fire_danger_rating_days, summed over those ratings)"""
    with xr.open_dataset(FWI_SUMMARY) as ds:
        if stat == "season_mean":
            days = {4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31}
            w = xr.DataArray(list(days.values()), dims="month", coords=dict(month=list(days)))
            f = ds.fwi_mean.weighted(w).mean("month").values
        elif stat == "peak_week":
            f = ds.fwi_doy.rolling(day=7, center=True).mean().max("day").values
        elif stat == "high_days":
            f = ds.summer_days.sel(rating=list(FWI_HIGH)).sum("rating", skipna=False).values
        else:
            raise ValueError(stat)
        lat, lon, names = ds.lat.values, ds.lon.values, list(ds.model.values)
    res = float(lon[1] - lon[0])
    assert lat[0] > lat[-1] and np.isclose(lat[0] - lat[1], res)
    return f, Affine(res, 0, lon[0] - res / 2, 0, -res, lat[0] + res / 2), names


def fwi(stat="season_mean"):
    """4-model mean of fwi_models(stat) on the GIPL grid: (values, na). Bilinear from the ~25 km cells; land cells
    inside the release's boreal domain that bilinear leaves blank (next to ocean cells) take the nearest cell. na =
    land outside the boreal domain (no fire weather data): fixed class Low (user, 2026-11-10)."""
    f, tr, _ = fwi_models(stat)
    f = f.mean(0)
    v = G.to_grid(f, tr, G.Resampling.bilinear, np.nan, crs="EPSG:4326")
    near = G.to_grid(f, tr, G.Resampling.nearest, np.nan, crs="EPSG:4326")
    fill = ~np.isfinite(v) & np.isfinite(near)
    v[fill] = near[fill]
    return v, G.land() & ~np.isfinite(v)
