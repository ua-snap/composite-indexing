"""PTI.md section 3: results figures, one per area (Statewide, Arctic, Interior, West, South) x scenario.

Each figure: rows = eras (2026-2050, 2051-2080, 2081-2100); columns = V1 table, V1 map, V2 table, V2 map.
Table panels: the two-way table on temperature axes, cell density (grey), marginal histograms, and the share of the
area's permafrost cells in each box. Maps: the area's cells by class; other permafrost cells in light grey.
Also writes <data>/results/t4/pti_area_summary.csv (class shares, medians, GIPL coverage per area x version x
scenario x era) for the text of section 3.
Outputs: docs/figures/pti_<area>_<rcp>.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap

from composite_indexing import config as C
from pti_draft_figures import ERAS, REGIONS, SCENS, box_share, load, table_with_marginals
from t4_index_variants import CLASS_C, CLASSES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
RES = C.DATA / "results/t4"
AREAS = [(0, "Statewide")] + list(REGIONS.items())
VNAME = {"V1": "V1 (air warming)", "V2": "V2 (GIPL warming)"}
INK, CONTEXT = "#0b0b0b", "#e4e3df"
CMAP = ListedColormap(CLASS_C)
CMAP.set_bad((0, 0, 0, 0))


def crop_of(mask, q=0.3, pad=15):
    rr, cc = np.nonzero(mask)
    r0, r1 = int(np.percentile(rr, q)) - pad, int(np.percentile(rr, 100 - q)) + pad
    c0, c1 = int(np.percentile(cc, q)) - pad, int(np.percentile(cc, 100 - q)) + pad
    return max(r0, 0), min(r1, mask.shape[0]), max(c0, 0), min(c1, mask.shape[1])


def class_map(ax, c, area, dom, crop, title):
    r0, r1, c0, c1 = crop
    ctx = np.where(dom & ~area, 1.0, np.nan)[r0:r1, c0:c1]
    ax.imshow(ctx, cmap=ListedColormap([CONTEXT]), vmin=0, vmax=2, interpolation="nearest")
    ax.imshow(np.where(area, c, np.nan)[r0:r1, c0:c1], cmap=CMAP, vmin=-0.5, vmax=len(CLASSES) - 0.5, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title(title, loc="left", fontsize=10)


def main():
    today, warm, cls, reg, dom = load()
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        gipl_ok = s.read(1) == 2
    rows = []
    for k, area_name in AREAS:
        area = dom & ((reg == k) if k else True)
        crop = crop_of(area)
        for scen in SCENS:
            fig = plt.figure(figsize=(23, 17))
            gs = fig.add_gridspec(len(ERAS), 4, width_ratios=[1.15, 1, 1.15, 1], wspace=0.18, hspace=0.32)
            for a, era in enumerate(ERAS):
                for b, ver in enumerate(["V1", "V2"]):
                    t, w = today[area], warm[(ver, scen, era)][area]
                    ax_t = fig.add_subplot(gs[a, 2 * b])
                    table_with_marginals(ax_t, t, w, f"{VNAME[ver]}, {era.replace('_', '–')}",
                                         annotate=box_share(t, w))
                    ax_m = fig.add_subplot(gs[a, 2 * b + 1])
                    class_map(ax_m, cls[(ver, scen, era)], area, dom, crop, f"{VNAME[ver]}, {era.replace('_', '–')}")
                    c = cls[(ver, scen, era)][area]
                    c = c[np.isfinite(c)]
                    rows.append(dict(area=area_name, version=ver, scen=scen, era=era, cells=int(area.sum()),
                                     today_median=float(np.nanmedian(t)), warming_median=float(np.nanmedian(w)),
                                     gipl_share=float(np.mean(gipl_ok[area])),
                                     **{cn: float(np.mean(c == q)) for q, cn in enumerate(CLASSES)}))
            handles = [plt.Rectangle((0, 0), 1, 1, fc=col) for col in CLASS_C] + \
                [plt.Rectangle((0, 0), 1, 1, fc=CONTEXT)]
            labels = CLASSES + (["other permafrost cells"] if k else [])
            fig.legend(handles[:len(labels)], labels, loc="upper center", ncol=6, frameon=False, fontsize=12,
                       bbox_to_anchor=(0.5, 0.955))
            fig.suptitle(f"{area_name} ({int(area.sum()):,} permafrost cells): RCP {scen[3]}.{scen[4]}", fontsize=15,
                         y=0.985)
            fig.savefig(FIG / f"pti_{area_name.lower()}_{scen}.png", dpi=110, bbox_inches="tight")
            plt.close(fig)
            print(area_name, scen, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "pti_area_summary.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_rows", 200):
        print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
