"""PTI.md extra figures:
  pti_v1_v2_count.png  - per cell: in how many of the 6 scenario x era combinations V1 and V2 give different classes,
                         and in which direction (V2 higher / lower / both). Cells where GIPL is masked are shown apart
                         (V2 = V1 there by construction).
  pti_v1_v2_bars.png   - share of each area's cells where V2 is higher / lower than V1, per scenario x era.
  pti_test_areas.png    - where the three test areas (data-sentence examples; "pilot windows" in the code) are.
Also <data>/results/t4/v1_v2_differences.csv: per area x scenario x era, the share of GIPL-used cells where the classes
differ (V2 higher / lower; two_plus = by 2+ classes). Rows with scen = era = "any" cover all 6 combinations:
v2_higher / v2_lower = only higher / only lower, v2_both = higher in some and lower in others, combos_k = share of
cells that differ in k combinations.
"""
import json
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
from scipy import ndimage

from composite_indexing import config as C
from pti_draft_figures import ERAS, REGIONS, SCENS, load
from pti_results_figures import crop_of

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
RES = C.DATA / "results/t4"
INK, INK2, GRID, CONTEXT = "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d4"
LOWER, HIGHER, BOTH, NOGIPL = "#2a78d6", "#e34948", "#7f6bb3", "#a3a19b"
COMBOS = [(s, e) for s in SCENS for e in ERAS]


def off(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)


def main():
    today, warm, cls, reg, dom = load()
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        gipl_ok = s.read(1) == 2
    comp = dom & gipl_ok  # cells where V2 really uses GIPL
    diffs = np.stack([cls[("V2", s, e)] - cls[("V1", s, e)] for s, e in COMBOS])  # (6, y, x)
    n_diff = np.sum(diffs != 0, axis=0)
    up, down = np.any(diffs > 0, axis=0), np.any(diffs < 0, axis=0)

    # --- table
    rows = []
    for k, rn in [(0, "Statewide")] + list(REGIONS.items()):
        m = comp & ((reg == k) if k else True)
        for q, (s, e) in enumerate(COMBOS):
            d = diffs[q][m]
            rows.append(dict(area=rn, scen=s, era=e, cells=int(m.sum()), differ=np.mean(d != 0),
                             v2_higher=np.mean(d > 0), v2_lower=np.mean(d < 0), two_plus=np.mean(np.abs(d) >= 2)))
        rows.append(dict(area=rn, scen="any", era="any", cells=int(m.sum()), differ=np.mean(n_diff[m] > 0),
                         v2_higher=np.mean(up[m] & ~down[m]), v2_lower=np.mean(down[m] & ~up[m]),
                         two_plus=np.mean((np.abs(diffs[:, m]) >= 2).any(axis=0)), v2_both=np.mean(up[m] & down[m]),
                         **{f"combos_{k}": np.mean(n_diff[m] == k) for k in range(3)},
                         combos_3plus=np.mean(n_diff[m] >= 3)))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "v1_v2_differences.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(df.round(3).to_string(index=False))
    m = comp
    print("count distribution (GIPL cells):", {k: round(float(np.mean(n_diff[m] == k)), 3) for k in range(7)})

    # --- maps
    r0, r1, c0, c1 = crop_of(dom)
    fig, axs = plt.subplots(1, 2, figsize=(16, 7), constrained_layout=True)
    seq = ListedColormap(["#f0efec", "#9ec5f4", "#3987e5", "#0d366b"])  # 0, 1, 2, 3+ combinations
    seq.set_bad((0, 0, 0, 0))
    for ax in axs:
        ax.imshow(np.where(dom & ~gipl_ok, 1.0, np.nan)[r0:r1, c0:c1], cmap=ListedColormap([NOGIPL]), vmin=0, vmax=2,
                  interpolation="nearest")
        off(ax)
    im = axs[0].imshow(np.where(comp, np.minimum(n_diff, 3), np.nan)[r0:r1, c0:c1], cmap=seq, vmin=-0.5, vmax=3.5,
                       interpolation="nearest")
    cb = fig.colorbar(im, ax=axs[0], shrink=0.6, ticks=range(4))
    cb.ax.set_yticklabels(["0", "1", "2", "3 or more"])
    cb.set_label("combinations (of 6) where V1 and V2 give different classes")
    axs[0].set_title("How often V1 and V2 disagree (2 scenarios × 3 eras)", loc="left", fontsize=11)
    dirn = np.full(dom.shape, np.nan)
    dirn[comp & (n_diff == 0)] = 0
    dirn[comp & up & ~down] = 1
    dirn[comp & down & ~up] = 2
    dirn[comp & up & down] = 3
    axs[1].imshow(dirn[r0:r1, c0:c1], cmap=ListedColormap(["#f0efec", HIGHER, LOWER, BOTH]), vmin=-0.5, vmax=3.5,
                  interpolation="nearest")
    axs[1].set_title("Which way V2 differs from V1", loc="left", fontsize=11)
    h = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in ["#f0efec", HIGHER, LOWER, BOTH, NOGIPL]]
    axs[1].legend(h, ["same class in all 6", "V2 higher class (in some)", "V2 lower class (in some)",
                      "both, depending on scenario / era", "GIPL masked: V2 = V1 by construction"],
                  loc="lower left", frameon=True, fontsize=9, framealpha=0.9)
    fig.savefig(FIG / "pti_v1_v2_count.png", dpi=120, bbox_inches="tight")
    plt.close(fig)

    # --- bars per area x combo
    areas = ["Statewide"] + list(REGIONS.values())
    fig, axs = plt.subplots(1, len(areas), figsize=(17, 4.2), sharey=True)
    for ax, a in zip(axs, areas):
        d = df[(df.area == a) & (df.scen != "any")]
        x = np.arange(len(d))
        ax.bar(x, 100 * d.v2_higher, color=HIGHER, width=0.75, label="V2 higher class")
        ax.bar(x, 100 * d.v2_lower, bottom=100 * d.v2_higher, color=LOWER, width=0.75, label="V2 lower class")
        ax.set_xticks(x, [f"{e[:4]}–{e[-2:]}\nRCP {s[3]}.{s[4]}" for s, e in zip(d.scen, d.era)], fontsize=7)
        ax.set_title(a, loc="left", fontsize=10)
        ax.grid(axis="y", color=GRID, lw=0.6)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    axs[0].set_ylabel("% of cells where V1 and V2 differ")
    axs[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "pti_v1_v2_bars.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # --- test-area locator
    wins = json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        tr = s.transform
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(np.where(dom, 1.0, np.nan)[r0:r1, c0:c1], cmap=ListedColormap([CONTEXT]), vmin=0, vmax=2,
              interpolation="nearest")
    for k, rn in REGIONS.items():
        mk = (reg == k)[r0:r1, c0:c1]
        ax.contour(mk.astype(float), levels=[0.5], colors=INK2, linewidths=0.7)
        lab, n = ndimage.label(mk & dom[r0:r1, c0:c1])
        big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
        cy, cx = ndimage.center_of_mass(lab == big)
        dx, dy = {"Interior": (-260, -40)}.get(rn, (0, 0))  # keep clear of the Fairbanks window label
        ax.text(cx + dx, cy + dy, rn, ha="center", va="center", fontsize=11, color=INK2, style="italic")
    for w in wins:
        col = ((w["x0"] + w["x1"]) / 2 - tr.c) / tr.a - c0
        row = ((w["y0"] + w["y1"]) / 2 - tr.f) / tr.e - r0
        ax.plot(col, row, "s", ms=11, mfc="none", mec=INK, mew=2)
        ax.annotate(f"{w['label']}\n{w['centre_lat']:.2f}°N {-w['centre_lon']:.2f}°W", (col, row), xytext=(10, 6),
                    textcoords="offset points", fontsize=9.5, weight="bold",
                    bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
    off(ax)
    ax.set_title("Test areas (10 × 10 km; squares enlarged) and regions; grey = permafrost cells", loc="left",
                 fontsize=10)
    fig.savefig(FIG / "pti_test_areas.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
