"""Map of the GIPL "stuck" magt1m cells in the Fairbanks pilot window (see t3_esa_gipl_continuity.py).

Panels: terrain (hillshade + elevation contours), GIPL magt1m 100-yr range, ESA PFR 2020, GIPL surface year-to-year
variability; stuck cells outlined. Also prints terrain / GIPL-field statistics for stuck vs other cells.
Output: docs/figures/t3_stuck_map.png, <data>/results/t3_stuck_cell_stats.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import LightSource, LinearSegmentedColormap
from rasterio.windows import from_bounds

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DEM_TIF = C.PISR_DATA / "dem/arcticdem_v4.1_32m_dem_3338.tif"
REGION = "fairbanks"
INK, INK2 = "#0b0b0b", "#52514e"
SEQ = LinearSegmentedColormap.from_list("blue", ["#e8f1fc", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])


def read(path, b):
    with rasterio.open(path) as s:
        w = from_bounds(*b, s.transform).round_offsets().round_lengths()
        a = s.read(1, window=w, masked=True).astype(float).filled(np.nan)
        t = s.window_transform(w)
    return a, (t.c, t.c + a.shape[1] * t.a, t.f + a.shape[0] * t.e, t.f)


def cell_grid(values, sub):
    """(10, 10) array, north-up, from per-cell values of one window."""
    ix = sub.ix - sub.ix.min()
    iy = sub.iy.max() - sub.iy
    g = np.full((iy.max() + 1, ix.max() + 1), np.nan)
    g[iy.values, ix.values] = values
    return g


def outline(ax, sub, stuck):
    for r in sub[stuck].itertuples():
        ax.add_patch(plt.Rectangle((r.x - 500, r.y - 500), 1000, 1000, fill=False, ec=INK, lw=1.6))


def per_cell_mean(raster, ext, sub):
    """Mean of 32 m pixels whose centres fall in each 1 km cell."""
    ny, nx = raster.shape
    xs = ext[0] + (np.arange(nx) + 0.5) * (ext[1] - ext[0]) / nx
    ys = ext[3] - (np.arange(ny) + 0.5) * (ext[3] - ext[2]) / ny
    out = []
    for r in sub.itertuples():
        mx = (xs >= r.x - 500) & (xs < r.x + 500)
        my = (ys >= r.y - 500) & (ys < r.y + 500)
        out.append(np.nanmean(raster[np.ix_(my, mx)]))
    return np.array(out)


def main():
    cells = pd.read_csv(C.DATA / "windows/gipl_cells.csv")
    flag = pd.read_csv(C.DATA / "results/t3_stuck_flag.csv")
    m = (cells.region == REGION).values
    sub, stuck = cells[m].reset_index(drop=True), flag.stuck.values[m]
    w = [x for x in __import__("json").loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]
         if x["region"] == REGION][0]
    b = (w["x0"], w["y0"], w["x1"], w["y1"])

    dem, ext = read(DEM_TIF, b)
    tii, _ = read(C.TII_TIF, b)
    gy_, gx_ = np.gradient(dem, 32.0)
    slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))

    ds = xr.open_dataset(next((C.DATA / "rasdaman_cache").glob(f"crrel_gipl_outputs_nc_wcs_pilot_{REGION}_*.nc")))
    pt = dict(X=xr.DataArray(sub.x.values), Y=xr.DataArray(sub.y.values), method="nearest")
    g = ds.isel(model=0).sel(**pt)  # 5ModelAvg; dims (time, scenario, dim_0)
    m1 = g.magt1m_degC
    rng = (m1.max(("time", "scenario")) - m1.min(("time", "scenario"))).values
    iav = g.magtsurface_degC.isel(scenario=1).diff("time").std("time").values
    esa = xr.open_dataset(C.DATA / "esa/esa_pilot_cells.nc")
    pfr = esa.PFR.sel(year=2020).values[m]

    # --- statistics
    st = pd.DataFrame(dict(
        stuck=stuck, elev=per_cell_mean(dem, ext, sub), slope=per_cell_mean(slope, ext, sub),
        tii=per_cell_mean(tii, ext, sub), pfr2020=pfr, magt1m_range=rng, surface_iav=iav,
        permafrosttop_2021=g.permafrosttop_m.isel(time=0, scenario=1).values,
        permafrosttop_2100=g.permafrosttop_m.isel(time=79, scenario=1).values,
        talik_2100=g.talikthickness_m.isel(time=79, scenario=1).values,
    ))
    summ = st.groupby("stuck").agg(["median", "min", "max"]).T
    summ.columns = ["other", "stuck"]
    summ.to_csv(C.DATA / "results/t3_stuck_cell_stats.csv")
    print(summ.round(2).to_string())

    # --- figure
    hs = LightSource(azdeg=315, altdeg=45).hillshade(np.nan_to_num(dem, nan=np.nanmean(dem)), dx=32, dy=32)
    fig, axs = plt.subplots(2, 2, figsize=(10, 10), constrained_layout=True)
    a = axs[0, 0]
    a.imshow(hs, extent=ext, cmap="gray", vmin=0, vmax=1)
    levels = np.arange(np.floor(np.nanmin(dem) / 100) * 100, np.nanmax(dem) + 100, 100)
    cs = a.contour(dem, levels=levels, extent=ext, origin="upper", colors=INK2, linewidths=0.5)
    a.clabel(cs, levels[::2], fontsize=6, fmt="%d m")
    a.set_title("Terrain (ArcticDEM 32 m, 100 m contours)", loc="left", color=INK, fontsize=10)

    panels = [
        (axs[0, 1], cell_grid(rng, sub), "GIPL 1 m MAGT: change over 2021–2120 (°C)", SEQ, (0, None)),
        (axs[1, 0], cell_grid(pfr, sub), "ESA permafrost fraction 2020 (%)", SEQ, (0, 100)),
        (axs[1, 1], cell_grid(iav, sub), "GIPL surface: year-to-year std (°C, RCP 8.5)", SEQ, (0, None)),
    ]
    for ax, grid, title, cmap, (lo, hi) in panels:
        im = ax.imshow(grid, extent=b[0:1] + b[2:3] + b[1:2] + b[3:4], cmap=cmap, vmin=lo, vmax=hi)
        ax.set_title(title, loc="left", color=INK, fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.8)
    for ax in axs.flat:
        for v in np.arange(b[0], b[2] + 1, 1000):
            ax.axvline(v, color="white", lw=0.4, alpha=0.6)
        for v in np.arange(b[1], b[3] + 1, 1000):
            ax.axhline(v, color="white", lw=0.4, alpha=0.6)
        outline(ax, sub, stuck)
        ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3])
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"Fairbanks pilot window (10 × 10 km, centre {w['centre_lat']:.2f}°N {-w['centre_lon']:.2f}°W): "
                 f"black outlines = {int(stuck.sum())} GIPL cells whose 1 m MAGT never changes",
                 color=INK, fontsize=10.5)
    fig.savefig(C.REPO / "docs/figures/t3_stuck_map.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
