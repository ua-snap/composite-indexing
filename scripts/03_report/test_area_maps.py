"""Test-area class maps for the data-sentence sections of PTI.md and PTI_COMPOSITE.md.
One panel per test area (Brooks Range, Fairbanks, Denali), V2, RCP 8.5, 2051-2080 (the data-sentence combination):
1 km classes over a 40 x 40 km area around the test area; test area (10 x 10 km) outlined; the centre cell (the cell
described by the data sentence) marked; classes drawn semi-transparent over an ArcticDEM v4.1 (32 m, gap-filled)
hillshade lit from the south (azimuth 180 deg, altitude 45 deg), water from the ArcticDEM water mask (both READ-ONLY).
Outputs: docs/figures/pti_test_area_maps.png (two-way table), docs/figures/ptic_test_area_maps.png (composite)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap

from composite_indexing import config as C
from pti_draft_figures import load
from t4_index_variants import CLASS_C, CLASSES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
DEM = Path("/beegfs/CMIP6/jdpaul3/ArcticDEM-PISR_data/dem")  # READ-ONLY (ArcticDEM-PISR data)
INK, WATER = "#0b0b0b", "#9ec5f4"
HALF = 20  # cells (km) either side of the test-area centre
SUN_AZ, SUN_ALT = 180.0, 45.0  # light from the south, 45 deg above the horizon
ALPHA = 0.6  # class colours over the hillshade
CMAP = ListedColormap(CLASS_C)
CMAP.set_bad((0, 0, 0, 0))


def hillshade(z, res, az=SUN_AZ, alt=SUN_ALT):
    """Lambertian hillshade, 0-1. x = east, y = north (rows run south); az clockwise from north."""
    dzdx = np.gradient(z, axis=1) / res
    dzdy = -np.gradient(z, axis=0) / res
    n = np.sqrt(dzdx ** 2 + dzdy ** 2 + 1)
    a, h = np.radians(az), np.radians(alt)
    lx, ly, lz = np.sin(a) * np.cos(h), np.cos(a) * np.cos(h), np.sin(h)
    return np.clip((-dzdx * lx - dzdy * ly + lz) / n, 0, 1)


def windows():
    """Per test area: centre cell (same rule as the data sentences), map extent, hillshade and water."""
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    xc, yc = f.x.values, f.y.values  # cell centres
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        tr = s.transform
    out = []
    for w in json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]:
        # nearest cell centre to the window centre, as in t4 sentences() / t5 test_areas() (the window is 10 cells
        # wide, so its centre is a cell corner; argmin breaks the tie)
        cc = int(np.argmin(np.abs(xc - (w["x0"] + w["x1"]) / 2)))
        rc = int(np.argmin(np.abs(yc - (w["y0"] + w["y1"]) / 2)))
        x0, y1 = tr * (cc - HALF, rc - HALF)  # outer edges of the 40 x 40 km area
        x1, y0 = tr * (cc + HALF, rc + HALF)
        bounds = (x0, y0, x1, y1)
        with rasterio.open(DEM / "arcticdem_v4.1_32m_dem_3338_filled.tif") as s:
            win = rasterio.windows.from_bounds(*bounds, transform=s.transform)
            z = s.read(1, window=win, boundless=True, fill_value=np.nan).astype("float64")
            res = s.res[0]
        with rasterio.open(DEM / "arcticdem_v4.1_32m_water_3338.tif") as s:
            water = s.read(1, window=rasterio.windows.from_bounds(*bounds, transform=s.transform), boundless=True,
                           fill_value=0) == 1
        z = np.where(np.isfinite(z), z, np.nanmedian(z))
        out.append(dict(w=w, cc=cc, rc=rc, bounds=bounds, tr=tr, hs=hillshade(z, res), water=water))
    return out


def draw(cls, wins, title_prefix, out):
    fig, axs = plt.subplots(1, len(wins), figsize=(5.2 * len(wins), 5.6), constrained_layout=True)
    for ax, d in zip(axs, wins):
        w, cc, rc, (x0, y0, x1, y1), tr = d["w"], d["cc"], d["rc"], d["bounds"], d["tr"]
        ext = (x0, x1, y0, y1)
        ax.imshow(d["hs"], cmap="gray", vmin=0, vmax=1, extent=ext, interpolation="bilinear")
        ax.imshow(np.where(d["water"], 1.0, np.nan), cmap=ListedColormap([WATER]), vmin=0, vmax=2, extent=ext,
                  interpolation="nearest")
        sub = cls[rc - HALF:rc + HALF, cc - HALF:cc + HALF]
        ax.imshow(sub, cmap=CMAP, vmin=-0.5, vmax=4.5, extent=ext, alpha=ALPHA, interpolation="nearest")
        ax.add_patch(plt.Rectangle((w["x0"], w["y0"]), w["x1"] - w["x0"], w["y1"] - w["y0"], fill=False, ec=INK,
                                   lw=2))
        cx0, cy1 = tr * (cc, rc)
        for ec, lw in [("white", 2.4), (INK, 1.1)]:
            ax.add_patch(plt.Rectangle((cx0, cy1 - 1000), 1000, 1000, fill=False, ec=ec, lw=lw))
        ax.plot([x0 + 2000, x0 + 12000], [y0 + 2500] * 2, color=INK, lw=3)
        ax.text(x0 + 7000, y0 + 3200, "10 km", ha="center", va="bottom", fontsize=9, color=INK,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        ax.set_xticks([]); ax.set_yticks([])
        k = int(cls[rc, cc]) if np.isfinite(cls[rc, cc]) else None
        ax.set_title(f"{w['label']} test area (centre cell: {CLASSES[k] if k is not None else 'n/a'})", loc="left",
                     fontsize=10.5)
    h = [plt.Rectangle((0, 0), 1, 1, fc=c, alpha=ALPHA) for c in CLASS_C]
    h += [plt.Rectangle((0, 0), 1, 1, fc="#bdbdbd"), plt.Rectangle((0, 0), 1, 1, fc=WATER),
          plt.Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=2), plt.Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=1)]
    fig.legend(h, CLASSES + ["no permafrost (hillshade only)", "water", "test area (10 × 10 km)",
                             "centre cell (data sentence)"],
               loc="lower center", ncol=5, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, -0.13))
    fig.suptitle(f"{title_prefix}: V2, RCP 8.5, 2051–2080, 1 km cells over ArcticDEM hillshade (lit from the south)",
                 x=0.01, ha="left", fontsize=12)
    fig.savefig(FIG / out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(out, "done")


def main():
    wins = windows()
    _, _, cls, _, _ = load()
    draw(cls[("V2", "rcp85", "2051_2080")], wins, "PTI (two-way table)", "pti_test_area_maps.png")
    c = xr.open_dataset(C.DATA / "results/t5/ptic.nc")["class_V2_rcp85_2051_2080"].values
    draw(c, wins, "PTI-C (composite)", "ptic_test_area_maps.png")


if __name__ == "__main__":
    main()
