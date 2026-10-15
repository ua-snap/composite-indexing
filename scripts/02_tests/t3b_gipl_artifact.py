"""Investigate the GIPL "stuck" magt1m artefact using the source GeoTIFFs (<data>/gipl_tif/<var>/, unzipped from
SNAP's CKAN archive).

  ingest   - are the GeoTIFFs identical to what Rasdaman served (grid + values at the pilot cells)?
  region   - 100 x 100 km around the Fairbanks pilot window: per-cell diagnostics + maps
             (5ModelAvg; magt1m change, surface year-to-year std, permafrost top, talik; terrain).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import LightSource, LinearSegmentedColormap
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TIF = C.DATA / "gipl_tif"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
YEARS = np.arange(2021, 2121)
UNITS = {"magt1m": "degC", "magtsurface": "degC", "permafrosttop": "m", "talikthickness": "m"}
INK, INK2 = "#0b0b0b", "#52514e"
SEQ = LinearSegmentedColormap.from_list("blue", ["#e8f1fc", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
SEQ.set_bad("#d9d8d4")
HALF = 50_000  # region half-width, m


def tif(var, year, model="5ModelAvg", scen="rcp85"):
    return TIF / var / f"gipl_{model}_{scen}_{var}_{UNITS[var]}_{year}.tif"


def stack(var, window, model="5ModelAvg", scen="rcp85"):
    """(year, row, col) float array for a raster window; nodata -> NaN."""
    out = []
    for y in YEARS:
        with rasterio.open(tif(var, y, model, scen)) as s:
            a = s.read(1, window=window, masked=True).astype(float).filled(np.nan)
        out.append(a)
    return np.stack(out)


def ingest():
    p = tif("magt1m", 2021)
    with rasterio.open(p) as s:
        print(p.name, s.crs, s.shape, s.dtypes, s.nodata, "\n", s.transform, "\n", s.bounds, s.tags())
        same = (np.isclose(s.bounds.left, C.GIPL_X0, atol=1) and np.isclose(s.bounds.bottom, C.GIPL_Y0, atol=1)
                and s.shape == (C.GIPL_NY, C.GIPL_NX))
        print("grid identical to Rasdaman crrel_gipl:", same)
        tr = s.transform
    cells = pd.read_csv(C.DATA / "windows/gipl_cells.csv")
    ds = {r: xr.open_dataset(next((C.DATA / "rasdaman_cache").glob(f"crrel_gipl_outputs_nc_wcs_pilot_{r}_*.nc")))
          for r in cells.region.unique()}
    rows, cols = rasterio.transform.rowcol(tr, cells.x.values, cells.y.values)
    worst = 0.0
    for var, field in [("magt1m", "magt1m_degC"), ("magtsurface", "magtsurface_degC")]:
        for mi, model in enumerate(["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"]):
            for si, scen in enumerate(["rcp45", "rcp85"]):
                for k in [0, 4, 29, 79, 99]:
                    with rasterio.open(tif(var, YEARS[k], model, scen)) as s:
                        a = s.read(1)
                    t = a[rows, cols].astype(float)
                    r = np.concatenate([ds[reg][field].isel(model=mi, scenario=si, time=k).sel(
                        X=xr.DataArray(cells.x.values[cells.region == reg]),
                        Y=xr.DataArray(cells.y.values[cells.region == reg]), method="nearest").values
                        for reg in cells.region.unique()])
                    worst = max(worst, float(np.nanmax(np.abs(t - r))))
    print(f"max |GeoTIFF - Rasdaman| over 300 cells x 3 models x 2 scen x 5 years x 2 vars: {worst:.4f}")


def region_window():
    w = [x for x in json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]
         if x["region"] == "fairbanks"][0]
    cx, cy = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
    with rasterio.open(tif("magt1m", 2021)) as s:
        win = from_bounds(cx - HALF, cy - HALF, cx + HALF, cy + HALF, s.transform).round_offsets().round_lengths()
        return win, s.window_transform(win), s.window_bounds(win), w


def terrain(bounds, shape):
    """DEM mean and slope per 1 km cell (from a 128 m decimated read of the 32 m ArcticDEM)."""
    with rasterio.open(C.PISR_DATA / "dem/arcticdem_v4.1_32m_dem_3338.tif") as s:
        w = from_bounds(*bounds, s.transform)
        dem = s.read(1, window=w, out_shape=(shape[0] * 8, shape[1] * 8),  # 125 m
                     resampling=Resampling.average, masked=True).astype(float).filled(np.nan)
    gy, gx = np.gradient(dem, 125.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    return dem, _block(dem, shape), _block(slope, shape)


def _block(a, shape):
    """Mean of a fine array over a coarse (shape) grid; trims edge pixels that do not divide evenly."""
    fy, fx = a.shape[0] // shape[0], a.shape[1] // shape[1]
    a = a[: shape[0] * fy, : shape[1] * fx]
    return np.nanmean(a.reshape(shape[0], fy, shape[1], fx), axis=(1, 3))


def region():
    OUT.mkdir(parents=True, exist_ok=True)
    win, tr, bounds, pilot = region_window()
    print("region window", win, bounds)
    d = {}
    for scen in ["rcp45", "rcp85"]:
        m1 = stack("magt1m", win, scen=scen)
        d[f"magt1m_range_{scen}"] = np.nanmax(m1, 0) - np.nanmin(m1, 0)
    ms = stack("magtsurface", win)
    d["surface_iav"] = np.nanstd(np.diff(ms, axis=0), axis=0)
    d["surface_change"] = np.nanmean(ms[-20:], 0) - np.nanmean(ms[5:15], 0)
    m1 = stack("magt1m", win)
    d["magt1m_2026_35"] = np.nanmean(m1[5:15], 0)
    d["magt1m_change"] = np.nanmean(m1[60:80], 0) - d["magt1m_2026_35"]  # 2081-2100 minus 2026-2035
    pt = stack("permafrosttop", win)
    d["pftop_2026_35"], d["pftop_2081_2100"] = np.nanmean(pt[5:15], 0), np.nanmean(pt[60:80], 0)
    d["talik_2081_2100"] = np.nanmean(stack("talikthickness", win)[60:80], 0)
    d["magt1m_range"] = np.fmax(d["magt1m_range_rcp45"], d["magt1m_range_rcp85"])
    dem, d["elev"], d["slope"] = terrain(bounds, d["magt1m_range"].shape)

    df = pd.DataFrame({k: v.ravel() for k, v in d.items()})
    df["valid"] = np.isfinite(df.magt1m_range)
    df["stuck"] = df.valid & (df.magt1m_range < 0.1)
    df.to_csv(OUT / "fairbanks100_cells.csv", index=False)
    v = df[df.valid]
    print(f"valid cells {len(v)}; stuck (1 m range < 0.1) {v.stuck.sum()} ({v.stuck.mean():.1%})")
    print("surface_iav quantiles:", np.nanpercentile(v.surface_iav, [1, 5, 10, 25, 50, 75, 90]).round(3))
    print(v.groupby("stuck")[["elev", "slope", "surface_iav", "magt1m_2026_35", "pftop_2026_35",
                               "pftop_2081_2100", "talik_2081_2100", "surface_change"]].median().round(2).T)
    np.savez_compressed(OUT / "fairbanks100_grids.npz", bounds=np.array(bounds), **d)
    plot_region(d, dem, bounds, pilot)


def plot_region(d, dem, bounds, pilot):
    ext = (bounds[0], bounds[2], bounds[1], bounds[3])
    hs = LightSource(azdeg=315, altdeg=45).hillshade(np.nan_to_num(dem, nan=np.nanmean(dem)), dx=125, dy=125)
    stuck = (d["magt1m_range"] < 0.1).astype(float)
    stuck[~np.isfinite(d["magt1m_range"])] = np.nan
    panels = [
        ("Terrain (ArcticDEM)", None, None, None),
        ("GIPL 1 m MAGT: max change over 2021–2120 (°C)", d["magt1m_range"], SEQ, (0, 6)),
        ("GIPL surface: year-to-year std (°C, RCP 8.5)", d["surface_iav"], SEQ, (0, 0.7)),
        ("GIPL permafrost top 2026–2035 (m)", d["pftop_2026_35"], SEQ, (0, 5)),
    ]
    fig, axs = plt.subplots(2, 2, figsize=(11, 11), constrained_layout=True)
    for ax, (title, grid, cmap, lim) in zip(axs.flat, panels):
        if grid is None:
            ax.imshow(hs, extent=ext, cmap="gray", vmin=0, vmax=1)
            ax.contour(np.where(np.isfinite(stuck), stuck, 0), levels=[0.5], extent=ext, origin="upper",
                       colors="#eb6834", linewidths=1.2)
        else:
            ax.imshow(hs, extent=ext, cmap="gray", vmin=0, vmax=1)
            im = ax.imshow(grid, extent=ext, cmap=cmap, vmin=lim[0], vmax=lim[1], alpha=0.85)
            fig.colorbar(im, ax=ax, shrink=0.75)
        ax.add_patch(plt.Rectangle((pilot["x0"], pilot["y0"]), 10_000, 10_000, fill=False, ec=INK, lw=1.2))
        ax.set_title(title, loc="left", color=INK, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    axs[0, 0].text(0.01, 0.01, "orange outline = stuck cells (1 m change < 0.1 °C)", transform=axs[0, 0].transAxes,
                   color=INK, fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.8))
    fig.suptitle("GIPL 2.0 (5ModelAvg) around Fairbanks, 100 × 100 km; black square = pilot window",
                 color=INK, fontsize=11)
    fig.savefig(FIG / "t3b_fairbanks100_map.png", dpi=140, bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(6, 3.4))
    v = d["surface_iav"][np.isfinite(d["surface_iav"])]
    ax.hist(v, bins=np.linspace(0, max(0.8, v.max()), 81), color="#2a78d6")
    ax.set_xlabel("GIPL surface year-to-year std (°C)"); ax.set_ylabel("cells")
    ax.set_title("Fairbanks 100 × 100 km: is the artefact a separate population?", loc="left", fontsize=10)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.savefig(FIG / "t3b_fairbanks100_iav_hist.png", dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["ingest", "region"])
    {"ingest": ingest, "region": region}[ap.parse_args().mode]()
