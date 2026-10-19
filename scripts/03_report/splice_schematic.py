"""ESA_GIPL_SPLICING.md: schematic of the delta change method for one made-up cell (round numbers, same as the doc's
worked example). ESA 2014-2023 level + bridge (expected warming to 2026-2035) = starting level for every later year;
GIPL contributes only its change after 2026-2035; GIPL's own level is never used.
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
ESA, BRIDGE = -2.0, 1.0
GIPL = {(2026, 2035): -4.0, (2051, 2080): -1.5, (2081, 2100): -0.5}


def fmt(v, sign=True):
    return (f"{v:+.1f}" if sign else f"{v:.1f}").replace("-", "\u2212")


def style(ax, ylim):
    ax.axvspan(2021, 2026, color=GRID, alpha=0.7, lw=0)
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
    base = GIPL[(2026, 2035)]
    start = ESA + BRIDGE
    fig, (top, bot) = plt.subplots(2, 1, figsize=(11, 8.6), sharex=True, gridspec_kw=dict(hspace=0.35))

    # --- top: what we take from GIPL (its change only)
    style(top, (-5.2, 0.6))
    top.text(2023.5, -4.7, "GIPL start-up\n(not used)", ha="center", va="center", fontsize=8.5, color=INK2)
    top.plot([2026, 2100], [base, base], color=GIPL_C, lw=1.2, ls=(0, (3, 3)), alpha=0.8)
    for (y0, y1), v in GIPL.items():
        top.plot([y0, y1], [v, v], color=GIPL_C, lw=5, solid_capstyle="butt")
        top.text((y0 + y1) / 2, v + 0.2, f"{fmt(v)} °C", ha="center", va="bottom", fontsize=9, color=INK2)
        if (y0, y1) != (2026, 2035):
            change_arrow(top, y0 + 3, base, v, f"GIPL change\n{fmt(v - base)} °C")
    top.text(2101, base, "GIPL's own 2026–2035\nlevel: NOT used", ha="left", va="center", fontsize=9, color=INK)
    top.set_title("1. What we take from GIPL: only how much it warms after 2026–2035 (its levels are not used)",
                  loc="left", fontsize=10.5)

    # --- bottom: the joined record, built from ESA
    style(bot, (-2.9, 3.4))
    bot.plot([2014, 2023], [ESA, ESA], color=ESA_C, lw=5, solid_capstyle="butt")
    bot.text(2018.5, ESA - 0.2, f"ESA 2014–2023\n{fmt(ESA)} °C", ha="center", va="top", fontsize=9, color=INK)
    bot.annotate("", xy=(2026, start), xytext=(2023, ESA),
                 arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4, mutation_scale=14))
    bot.text(2024.5, start + 0.35, f"+ bridge {fmt(BRIDGE)} °C\n(expected warming,\n2014–2023 → 2026–2035)",
             ha="center", va="bottom", fontsize=9, color=INK)
    bot.plot([2026, 2100], [start, start], color=JOIN_C, lw=1.2, ls=(0, (3, 3)))
    bot.text(2101, start, f"ESA + bridge = {fmt(start)} °C:\nthe starting level for\nevery later year",
             ha="left", va="center", fontsize=9, color=INK)
    for (y0, y1), v in GIPL.items():
        joined = start + (v - base)
        bot.plot([y0, y1], [joined, joined], color=JOIN_C, lw=5, solid_capstyle="butt")
        if (y0, y1) == (2026, 2035):
            continue
        ch = v - base
        change_arrow(bot, y0 + 3, start, joined, f"+ GIPL change\n{fmt(ch)} °C (from panel 1)")
        bot.text((y0 + y1) / 2, joined + 0.2,
                 f"{fmt(ESA)} + {fmt(BRIDGE, False)} + {fmt(ch, False)} = {fmt(joined)} °C",
                 ha="center", va="bottom", fontsize=9, color=INK, weight="bold")
    bot.set_title("2. The joined record: start from ESA, add the bridge, then add GIPL's change", loc="left",
                  fontsize=10.5)
    fig.suptitle("Delta change method, one example cell (round numbers)", x=0.125, ha="left", fontsize=12, y=0.97)
    fig.savefig(FIG / "t3_delta_method_schematic.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
