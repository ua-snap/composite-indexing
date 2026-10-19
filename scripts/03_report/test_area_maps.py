"""Test-area class maps for the data-sentence sections of PTI.md and PTI_COMPOSITE.md.
One panel per test area (Brooks Range, Fairbanks, Denali), V2, RCP 8.5, 2051-2080 (the data-sentence combination):
1 km classes over a 40 x 40 km area around the test area; test area (10 x 10 km) outlined; the centre cell (the cell
described by the data sentence) marked.
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
INK, NOPF = "#0b0b0b", "#f0efec"
HALF = 20  # cells (km) either side of the test-area centre
CMAP = ListedColormap(CLASS_C)
CMAP.set_bad((0, 0, 0, 0))


def draw(cls, title_prefix, out):
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    xc, yc = f.x.values, f.y.values  # cell centres
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        tr = s.transform
    wins = json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]
    fig, axs = plt.subplots(1, len(wins), figsize=(5.2 * len(wins), 5.6), constrained_layout=True)
    for ax, w in zip(axs, wins):
        c0, r0 = ~tr * (w["x0"], w["y1"])  # window edges -> fractional col/row
        c1, r1 = ~tr * (w["x1"], w["y0"])
        # centre cell: same rule as the data sentences (t4 sentences(), t5 test_areas()): nearest cell centre to the
        # window centre (the window is 10 cells wide, so its centre is a cell corner; argmin breaks the tie)
        cc = int(np.argmin(np.abs(xc - (w["x0"] + w["x1"]) / 2)))
        rc = int(np.argmin(np.abs(yc - (w["y0"] + w["y1"]) / 2)))
        sl = (slice(rc - HALF, rc + HALF), slice(cc - HALF, cc + HALF))
        sub = cls[sl]
        ax.imshow(np.where(np.isfinite(sub), np.nan, 1.0), cmap=ListedColormap([NOPF]), vmin=0, vmax=2,
                  interpolation="nearest")
        ax.imshow(sub, cmap=CMAP, vmin=-0.5, vmax=4.5, interpolation="nearest")
        ox, oy = cc - HALF, rc - HALF
        ax.add_patch(plt.Rectangle((c0 - ox - 0.5, r0 - oy - 0.5), c1 - c0, r1 - r0, fill=False, ec=INK, lw=2))
        ax.add_patch(plt.Rectangle((cc - ox - 0.5, rc - oy - 0.5), 1, 1, fill=False, ec="white", lw=2.2))
        ax.add_patch(plt.Rectangle((cc - ox - 0.5, rc - oy - 0.5), 1, 1, fill=False, ec=INK, lw=1))
        ax.plot([2, 12], [2 * HALF - 3] * 2, color=INK, lw=3)
        ax.text(7, 2 * HALF - 4, "10 km", ha="center", va="bottom", fontsize=9, color=INK,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
        ax.set_xticks([]); ax.set_yticks([])
        k = int(cls[rc, cc]) if np.isfinite(cls[rc, cc]) else None
        ax.set_title(f"{w['label']} test area (centre cell: {CLASSES[k] if k is not None else 'n/a'})", loc="left",
                     fontsize=10.5)
    h = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C] + [plt.Rectangle((0, 0), 1, 1, fc=NOPF, ec="#c9c7c1")]
    h += [plt.Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=2), plt.Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=1)]
    fig.legend(h, CLASSES + ["no permafrost (not scored)", "test area (10 × 10 km)", "centre cell (data sentence)"],
               loc="lower center", ncol=4, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, -0.13))
    fig.suptitle(f"{title_prefix}: V2, RCP 8.5, 2051–2080, 1 km cells", x=0.01, ha="left", fontsize=12)
    fig.savefig(FIG / out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(out, "done")


def main():
    _, _, cls, _, _ = load()
    draw(cls[("V2", "rcp85", "2051_2080")], "PTI (two-way table)", "pti_test_area_maps.png")
    c = xr.open_dataset(C.DATA / "results/t5/ptic.nc")["class_V2_rcp85_2051_2080"].values
    draw(c, "PTI-C (composite)", "ptic_test_area_maps.png")


if __name__ == "__main__":
    main()
