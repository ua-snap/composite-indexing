"""ESA_GIPL_SPLICING.md: why GIPL surface LEVELS rank like air temperature (rho ~0.95) but its WARMING does not
(rho ~0.26). Same cells, RCP 8.5, 2051-2080, 5ModelAvg / 5modelAvg, GIPL class 2 permafrost cells (D17).
(a) levels: air vs GIPL surface; (b) warming since 2026-2035 on the same 14 degC-wide axes as (a); (c) warming zoomed.
The scatter around the trend is similar in size (or smaller) for warming, but the range of warming across cells is
~7x narrower, so the same scatter scrambles the ranking.
Output: docs/figures/t3_levels_vs_changes.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import xarray as xr
from scipy.stats import spearmanr

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SPAN = 14.0  # degC shown on both axes of panels a and b


def main():
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    dom = (f.pfr_pos.values == 1) & (f.gipl_class.values == 2)
    m, g = f.maat_rcp85_2051_2080.values, f.gipl_sfc_rcp85_2051_2080.values
    dm, dg = m - f.maat_rcp85_base.values, g - f.gipl_sfc_rcp85_base.values
    ok = dom & np.isfinite(m) & np.isfinite(g) & np.isfinite(dm) & np.isfinite(dg)
    pairs = {"lev": (m[ok], g[ok]), "chg": (dm[ok], dg[ok])}
    st = {}
    for k, (x, y) in pairs.items():
        r = y - np.polyval(np.polyfit(x, y, 1), x)
        st[k] = dict(rho=spearmanr(x[::7], y[::7]).statistic,
                     rng=np.subtract(*np.percentile(x, [90, 10])),
                     sc=np.subtract(*np.percentile(r, [90, 10])) / 2)
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw=dict(width_ratios=[1, 1, 1]))
    lev_lim = (-8.0, -8.0 + SPAN)
    c = float(np.median(pairs["chg"][0]))
    chg_lim = (c - SPAN / 2, c + SPAN / 2)
    panels = [("lev", lev_lim, "a. Temperature levels"),
              ("chg", chg_lim, "b. Warming since 2026–2035, same scale as (a)"),
              ("chg", (0.5, 4.5), "c. Warming, zoomed in")]
    for ax, (k, lim, title) in zip(axs, panels):
        x, y = pairs[k]
        ax.hexbin(x, y, gridsize=90 if ax is not axs[1] else 140, bins="log", cmap="Blues", mincnt=1,
                  extent=(*lim, *lim), linewidths=0)
        ax.plot(lim, lim, color=INK2, lw=0.8, ls=(0, (3, 3)))
        ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
        ax.grid(color=GRID, lw=0.6)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        ax.set_title(title, loc="left", fontsize=10.5)
        s = st[k]
        ax.text(0.03, 0.97, f"Spearman ρ = {s['rho']:.2f}\nrange of cells: {s['rng']:.1f} °C\n"
                f"scatter around the trend: ±{s['sc']:.1f} °C", transform=ax.transAxes, ha="left", va="top",
                fontsize=9, color=INK, bbox=dict(fc="white", ec="none", alpha=0.85, pad=2))
    axs[0].set_xlabel("air temperature, 2051–2080 (°C)")
    axs[0].set_ylabel("GIPL ground surface temperature, 2051–2080 (°C)")
    for ax in axs[1:]:
        ax.set_xlabel("air warming (°C)")
        ax.set_ylabel("GIPL ground surface warming (°C)")
    axs[1].annotate("all cells sit\nin this small patch", xy=(c + 0.6, c + 0.3), xytext=(c + 2.5, c - 4.0),
                    fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    fig.text(0.5, -0.03, "Each panel: the same 724,326 permafrost cells where GIPL is usable, RCP 8.5, 5-model average; "
             "darker = more cells; dashed = 1:1. Range = 10th–90th percentile of air values; scatter = half the "
             "10th–90th percentile range of the residuals from a straight-line fit.", ha="center", fontsize=8.5,
             color=INK2, wrap=True)
    fig.tight_layout()
    fig.savefig(FIG / "t3_levels_vs_changes.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(st)


if __name__ == "__main__":
    main()
