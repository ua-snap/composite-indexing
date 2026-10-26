"""Concept diagram: three composite indices (Permafrost Thaw, Wildfire, Erosion), each with its own 3-tier rating,
combined into one 3-tier Environmental Hazard Index (EHI, the headline dashboard value). Equations are mock-ups.
Output: docs/figures/ehi_diagram.{svg,png}
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
INK, INK2, GRID, PANEL = "#0b0b0b", "#52514e", "#e4e3df", "#f6f5f2"
TIERS = [("Low", "#0072B2", "#ffffff"), ("Moderate", "#F0E442", INK), ("High", "#D55E00", INK)]  # name, fill, text
INDICES = [("Permafrost Thaw Index", "PTI", "today's surface\ntemperature", "projected\nwarming"),
           ("Wildfire Index", "WI", "ALFRESCO", "fire\nweather"),
           ("Erosion Index", "EI", "NG-IDF", "stream flow\nstats")]
W, H = 12.0, 7.15


def box(ax, x, y, w, h, fc, ec, lw=1.2, r=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))


def tiers(ax, xc, y, w=1.05, h=0.4, gap=0.08, fs=10):
    x0 = xc - (3 * w + 2 * gap) / 2
    for k, (name, fc, tc) in enumerate(TIERS):
        x = x0 + k * (w + gap)
        box(ax, x, y, w, h, fc, fc, lw=0, r=0.08)
        ax.text(x + w / 2, y + h / 2, name, ha="center", va="center", fontsize=fs, weight="bold", color=tc)


def main():
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    # top: headline index
    ex, ey, ew, eh = 3.2, 5.0, 5.6, 1.85
    box(ax, ex, ey, ew, eh, PANEL, INK, lw=2.0)
    ax.text(W / 2, ey + eh - 0.4, "Environmental Hazard Index (EHI)", ha="center", va="center", fontsize=17,
            weight="bold", color=INK)
    ax.text(W / 2, ey + eh - 0.88, "EHI = combine( PTI , WI , EI )", ha="center", va="center", fontsize=10.5,
            color=INK, family="DejaVu Sans Mono")
    tiers(ax, W / 2, ey + 0.2, w=1.45, h=0.5, fs=12)

    # bottom: contributing indices
    bw, bh, by = 3.6, 3.15, 0.25
    for k, (name, abbr, v1, v2) in enumerate(INDICES):
        bx = 0.3 + k * (bw + 0.3)
        xc = bx + bw / 2
        box(ax, bx, by, bw, bh, "#ffffff", INK2)
        ax.text(xc, by + bh - 0.32, f"{name} ({abbr})", ha="center", va="center", fontsize=12.5, weight="bold",
                color=INK)
        # mock equation: [variable 1] x [variable 2] = ABBR
        pw, ph, py = 1.35, 0.72, by + 1.6
        for j, v in enumerate([v1, v2]):
            px = xc - 0.12 - pw if j == 0 else xc + 0.12
            box(ax, px, py, pw, ph, GRID, GRID, lw=0, r=0.08)
            ax.text(px + pw / 2, py + ph / 2, v, ha="center", va="center", fontsize=9.5, color=INK, linespacing=1.1)
        ax.text(xc, py + ph / 2, "×", ha="center", va="center", fontsize=14, weight="bold", color=INK2)
        ax.text(xc, by + 1.22, f"= {abbr} rating", ha="center", va="center", fontsize=11, weight="bold", color=INK)
        tiers(ax, xc, by + 0.35)

        # arrow: each index passes its own 3-tier rating up to the EHI
        x_top = ex + ew * (k + 1) / 4
        ax.add_patch(FancyArrowPatch((xc, by + bh + 0.05), (x_top, ey - 0.05), arrowstyle="-|>", mutation_scale=20,
                                     lw=2.0, color=INK2, shrinkA=0, shrinkB=0))

    for ext in ["svg", "png"]:
        fig.savefig(FIG / f"ehi_diagram.{ext}", dpi=200, facecolor="#ffffff")
    plt.close(fig)


if __name__ == "__main__":
    main()
