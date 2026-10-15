"""Figures for docs/GIPL_ISSUE.md (local GIPL source GeoTIFFs; window reads only).

  gipl_issue_one_cell.png  - a stuck cell vs its nearest normal neighbour, all 6 runs: 1 m MAGT, surface MAGT,
                             permafrost-top depth.
  gipl_issue_six_runs.png  - 1 m MAGT change 2021-2120 in a 40 x 40 km area NE of Fairbanks, one panel per run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap
from pyproj import Transformer
from rasterio.windows import Window, from_bounds
from scipy import ndimage

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TIF = C.DATA / "gipl_tif"
FIG = C.REPO / "docs/figures"
YEARS = np.arange(2021, 2121)
MODELS = ["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"]
SCENS = ["rcp45", "rcp85"]
MODEL_C = {"5ModelAvg": "#2a78d6", "GFDL-CM3": "#eb6834", "NCAR-CCSM4": "#1baf7a"}
SCEN_LS = {"rcp45": "-", "rcp85": (0, (4, 2))}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
STUCK_XY = (322708.291, 1692979.751)  # Fairbanks pilot-window centre cell (65.05N 147.14W)
ZOOM_HALF = 20_000


def path(var, model, scen, year):
    unit = "degC" if var.startswith("magt") else "m"
    return TIF / var / f"gipl_{model}_{scen}_{var}_{unit}_{year}.tif"


def series(var, model, scen, row, col):
    out = []
    for y in YEARS:
        with rasterio.open(path(var, model, scen, y)) as s:
            out.append(float(s.read(1, window=Window(col, row, 1, 1))[0, 0]))
    a = np.array(out)
    a[a < -9000] = np.nan
    return a


def normal_neighbour(row, col):
    """Nearest cell (> 2 km away) that is 'good' in statewide_frozen_class (class 2)."""
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        w = Window(col - 15, row - 15, 31, 31)
        cls = s.read(1, window=w)
    rr, cc = np.nonzero(cls == 2)
    d = np.hypot(rr - 15, cc - 15)
    d[d <= 2] = np.inf
    k = np.argmin(d)
    return row - 15 + rr[k], col - 15 + cc[k]


def one_cell():
    with rasterio.open(path("magt1m", "5ModelAvg", "rcp85", 2021)) as s:
        row, col = s.index(*STUCK_XY)
        tr = s.transform
    nrow, ncol = normal_neighbour(row, col)
    to_ll = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})
    fig, axs = plt.subplots(2, 3, figsize=(13, 6.6), sharex=True)
    for i, (r, c, name) in enumerate([(row, col, "Stuck cell"), (nrow, ncol, "Normal neighbour")]):
        x, y = tr * (c + 0.5, r + 0.5)
        lon, lat = to_ll.transform(x, y)
        for j, (var, lab) in enumerate([("magt1m", "1 m MAGT (°C)"), ("magtsurface", "Surface MAGT (°C)"),
                                        ("permafrosttop", "Permafrost top depth (m)")]):
            ax = axs[i, j]
            ax.grid(axis="y", color=GRID, lw=0.6)
            for m in MODELS:
                for sc in SCENS:
                    ax.plot(YEARS, series(var, m, sc, r, c), color=MODEL_C[m], ls=SCEN_LS[sc], lw=1.6)
            if var.startswith("magt"):
                ax.axhline(0, color=INK2, lw=0.8, ls=(0, (2, 2)))
            ax.set_ylabel(lab)
            if j == 0:
                ax.set_title(f"{name} ({lat:.2f}°N {-lon:.2f}°W)", loc="left", fontsize=10, color=INK)
    for j in range(3):  # same y-range per variable for both cells; depth axis points down
        lo = min(axs[i, j].get_ylim()[0] for i in range(2))
        hi = max(axs[i, j].get_ylim()[1] for i in range(2))
        for i in range(2):
            axs[i, j].set_ylim((hi, 0) if j == 2 else (lo, hi))
    handles = [plt.Line2D([], [], color=MODEL_C[m], lw=2, label=m) for m in MODELS] + [
        plt.Line2D([], [], color=INK2, lw=1.6, ls=SCEN_LS[s], label=lab)
        for s, lab in zip(SCENS, ["RCP 4.5", "RCP 8.5"])]
    fig.legend(handles=handles, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "gipl_issue_one_cell.png", dpi=150, bbox_inches="tight")
    print("stuck cell", row, col, "normal neighbour", nrow, ncol)


def six_runs():
    cx, cy = STUCK_XY
    with rasterio.open(path("magt1m", "5ModelAvg", "rcp85", 2021)) as s:
        win = from_bounds(cx - ZOOM_HALF, cy - ZOOM_HALF, cx + ZOOM_HALF, cy + ZOOM_HALF,
                          s.transform).round_offsets().round_lengths()
        b = s.window_bounds(win)
    ext = (b[0], b[2], b[1], b[3])
    cmap = LinearSegmentedColormap.from_list("blue", ["#ffffff", "#e8f1fc", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    fig, axs = plt.subplots(2, 3, figsize=(12, 8.4), constrained_layout=True)
    for i, sc in enumerate(SCENS):
        for j, m in enumerate(MODELS):
            lo = hi = None
            for y in YEARS:
                with rasterio.open(path("magt1m", m, sc, y)) as s:
                    a = s.read(1, window=win).astype(float)
                lo = a if lo is None else np.minimum(lo, a)
                hi = a if hi is None else np.maximum(hi, a)
            rng = hi - lo
            ax = axs[i, j]
            im = ax.imshow(rng, extent=ext, cmap=cmap, vmin=0, vmax=6, interpolation="nearest")
            ax.contour(rng < 0.1, levels=[0.5], extent=ext, origin="upper", colors="#c2410c", linewidths=1.0)
            n = int((rng < 0.1).sum())
            ax.set_title(f"{m}, {sc.upper()[:3]} {sc[3]}.{sc[4]}: {n} stuck cells", loc="left", fontsize=10,
                         color=INK)
            ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axs, shrink=0.6, label="1 m MAGT change over 2021–2120 (max − min, °C)")
    fig.suptitle("Same cells stuck in every model and scenario (40 × 40 km NE of Fairbanks; orange outline = change "
                 "< 0.1 °C)", fontsize=11, color=INK)
    fig.savefig(FIG / "gipl_issue_six_runs.png", dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    one_cell()
    six_runs()
