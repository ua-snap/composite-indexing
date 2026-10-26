"""ESA_GIPL_SPLICING.md: schematic of the delta change method for one made-up cell (round numbers, same as the doc's
worked example). ESA 2014-2023 level = starting level for every later year; GIPL contributes only its change after
2014-2023 (GIPL climate years, GIPL_ISSUE_3.md: the same decade as ESA, so no bridge is needed); GIPL's own level is
never used.
Output: docs/figures/t3_delta_method_schematic.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
ESA_C, GIPL_C, JOIN_C = "#52514e", "#2a78d6", "#eb6834"  # as in t3_splice_pilots.png
ESA = -2.0
REF = (2014, 2023)
GIPL = {REF: -3.0, (2051, 2080): -0.5, (2081, 2100): 0.5}


def fmt(v, sign=True):
    return (f"{v:+.1f}" if sign else f"{v:.1f}").replace("-", "\u2212")


def style(ax, ylim):
    ax.axvspan(*REF, color=GRID, alpha=0.7, lw=0)
    ax.set_xlim(2010, 2100)
    ax.set_ylim(*ylim)
    ax.set_ylabel("°C")
    ax.grid(axis="y", color=GRID, lw=0.6)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)


def change_arrow(ax, x, lo, hi, text):
    ax.annotate("", xy=(x, hi), xytext=(x, lo), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2,
                                                                 mutation_scale=12))
    ax.text(x + 1.2, (lo + hi) / 2, text, ha="left", va="center", fontsize=9, color=INK2)


def main():
    base = GIPL[REF]
    fig, (top, bot) = plt.subplots(2, 1, figsize=(11, 8.6), sharex=True, gridspec_kw=dict(hspace=0.35))

    # --- top: what we take from GIPL (its change only)
    style(top, (-3.8, 1.6))
    top.plot([REF[1], 2100], [base, base], color=GIPL_C, lw=1.2, ls=(0, (3, 3)), alpha=0.8)
    for (y0, y1), v in GIPL.items():
        top.plot([y0, y1], [v, v], color=GIPL_C, lw=5, solid_capstyle="butt")
        top.text((y0 + y1) / 2, v + 0.2, f"{fmt(v)} °C", ha="center", va="bottom", fontsize=9, color=INK2)
        if (y0, y1) != REF:
            change_arrow(top, y0 + 3, base, v, f"GIPL change\n{fmt(v - base)} °C")
    top.text(2101, base, "GIPL's own 2014–2023\nlevel: NOT used", ha="left", va="center", fontsize=9, color=INK)
    top.set_title("1. What we take from GIPL: only how much it warms after 2014–2023 (its levels are not used)",
                  loc="left", fontsize=10.5)

    # --- bottom: the joined record, built from ESA
    style(bot, (-2.9, 2.6))
    bot.plot(REF, [ESA, ESA], color=ESA_C, lw=5, solid_capstyle="butt")
    bot.text(sum(REF) / 2, ESA - 0.2, f"ESA 2014–2023\n{fmt(ESA)} °C", ha="center", va="top", fontsize=9, color=INK)
    bot.plot([REF[1], 2100], [ESA, ESA], color=JOIN_C, lw=1.2, ls=(0, (3, 3)))
    bot.text(2101, ESA, f"ESA = {fmt(ESA)} °C:\nthe starting level for\nevery later year",
             ha="left", va="center", fontsize=9, color=INK)
    for (y0, y1), v in GIPL.items():
        if (y0, y1) == REF:
            continue
        ch = v - base
        joined = ESA + ch
        bot.plot([y0, y1], [joined, joined], color=JOIN_C, lw=5, solid_capstyle="butt")
        change_arrow(bot, y0 + 3, ESA, joined, f"+ GIPL change\n{fmt(ch)} °C (from panel 1)")
        bot.text((y0 + y1) / 2, joined + 0.2, f"{fmt(ESA)} + {fmt(ch, False)} = {fmt(joined)} °C",
                 ha="center", va="bottom", fontsize=9, color=INK, weight="bold")
    bot.set_title("2. The joined record: start from ESA, then add GIPL's change", loc="left", fontsize=10.5)
    bot.set_xlabel("Year (GIPL on the climate years it carries)")
    fig.suptitle("Delta change method, one example cell (round numbers)", x=0.125, ha="left", fontsize=12, y=0.97)
    fig.savefig(FIG / "t3_delta_method_schematic.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
