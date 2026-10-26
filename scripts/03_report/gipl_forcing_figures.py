"""Figures for docs/GIPL_ISSUE_3.md (which climate data drove GIPL 2.0, and which years). Reads <data>/results/t7/
(scripts/02_tests/t7_gipl_forcing.py). Writes docs/figures/gipl3_*.png."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

T7 = C.DATA / "results/t7"
FIG = Path(__file__).resolve().parents[2] / "docs/figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
RUN_C = {"5ModelAvg": "#2a78d6", "GFDL-CM3": "#eb6834", "NCAR-CCSM4": "#1baf7a"}
RUN_L = {"5ModelAvg": "5-model average", "GFDL-CM3": "GFDL-CM3", "NCAR-CCSM4": "NCAR-CCSM4"}
AIR_C, OBS_C = "#52514e", "#9a9893"
OLD_C, NEW_C = "#9ec5f4", "#1c5cab"
plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 10, "axes.titlelocation": "left"})


def clean(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.6)
        ax.set_axisbelow(True)


def fig_series():
    """GFDL-CM3 RCP 4.5: GIPL surface year-to-year changes vs air, as labelled and shifted by 20 years."""
    s = pd.read_csv(T7 / "series.csv")
    d = s[(s.run == "GFDL-CM3") & (s.scen == "rcp45")].set_index("gipl_year")
    g = d.gipl_surface.diff()
    same = d.model_air_same_year.diff()
    shifted = d.model_air_shifted.diff().where(d.forcing_year >= 2017)
    obs = d.cru_air.diff().where(d.forcing_year <= 2015)
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 5.2), sharex=True, sharey=True)
    for ax, air, title in [(axes[0], same, "(a) As labelled: GIPL year Y next to air temperature of year Y"),
                           (axes[1], shifted, "(b) Shifted: GIPL year Y next to air temperature of year Y − 20")]:
        ax.axhline(0, color=INK2, lw=0.6)
        ax.plot(air.index, air, color=AIR_C, lw=1.3, label="Air, GFDL-CM3 RCP 4.5 (SNAP 2 km)")
        if ax is axes[1]:
            ax.plot(obs.index, obs, color=OBS_C, lw=1.3, ls=(0, (3, 1.5)), label="Air, observed (CRU TS)")
        ax.plot(g.index, g, color=RUN_C["GFDL-CM3"], lw=1.8, label="GIPL ground surface")
        ax.set_title(title)
        ax.set_ylabel("Change from previous year (°C)")
        clean(ax)
    axes[1].axvline(2035.5, color=INK2, lw=0.8, ls=":")
    axes[1].text(2035.2, axes[1].get_ylim()[1] * 0.92, "observed | projected ", ha="right", va="top", color=INK2,
                 fontsize=8)
    axes[1].legend(loc="lower right", frameon=False, fontsize=8, ncol=3)
    axes[1].set_xlabel("GIPL year (as labelled in the files)")
    axes[1].set_xlim(2021, 2120)
    secax = axes[1].secondary_xaxis("top", functions=(lambda x: x - 20, lambda x: x + 20))
    secax.set_xlabel("Climate year it carries", fontsize=8.5, color=INK2)
    secax.tick_params(labelsize=8, colors=INK2)
    fig.tight_layout()
    fig.savefig(FIG / "gipl3_shift_series.png", dpi=200)
    plt.close(fig)


def fig_lagscan():
    t = pd.read_csv(T7 / "lagscan.csv")
    t = t[t.window == "2036-2095"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.axhline(0, color=INK2, lw=0.6)
    ax.axvline(20, color=GRID, lw=6, zorder=0)
    for run in RUN_C:
        for scen, ls in [("rcp45", "-"), ("rcp85", (0, (4, 2)))]:
            d = t[(t.run == run) & (t.scen == scen) & (t.source == f"2k_{run}_{scen}")].sort_values("offset")
            ax.plot(d.offset, d.median_r, color=RUN_C[run], ls=ls, lw=1.6)
            pk = d.loc[d.median_r.idxmax()]
            if run != "NCAR-CCSM4":
                ax.annotate(f"{RUN_L[run]} {scen[3]}.{scen[4]}: {pk.median_r:.2f} at {pk.offset:.0f} yr",
                            (pk.offset, pk.median_r), xytext=(8, 2 if scen == "rcp45" else -10),
                            textcoords="offset points", fontsize=8, color=INK)
    for run in RUN_C:
        ax.plot([], [], color=RUN_C[run], lw=4,
                label=RUN_L[run] + (" (no match at any shift)" if run == "NCAR-CCSM4" else ""))
    ax.plot([], [], color=INK2, lw=1.6, label="RCP 4.5")
    ax.plot([], [], color=INK2, lw=1.6, ls=(0, (4, 2)), label="RCP 8.5")
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    ax.set_xlim(-5, 30)
    ax.set_ylim(-0.6, 1.05)
    ax.set_xlabel("Shift: GIPL year Y compared with air temperature of year Y − shift")
    ax.set_ylabel("Match of year-to-year changes\n(median correlation per cell)")
    ax.set_title("GIPL ground surface 2036–2095 vs its own climate model's air temperature")
    clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "gipl3_lagscan.png", dpi=200)
    plt.close(fig)


def fig_bias():
    b = pd.read_csv(T7 / "bias20.csv")
    b = b[(b.run == "5ModelAvg") & (b.scen == "rcp85")]
    deps = [("magtsurface", "Surface"), ("magt1m", "1 m"), ("magt2m", "2 m")]
    regions = ["Arctic", "Interior", "West", "South"]
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.axhline(0, color=INK2, lw=0.8)
    w = 0.36
    for i, (dep, lab) in enumerate(deps):
        d = b[b.depth == dep].set_index("region")
        for k, (col, c, name) in enumerate([("old_excess_offset", OLD_C, "Years as labelled (GIPL_ISSUE_2)"),
                                            ("new_offset_vs_esa_same_years", NEW_C, "Same climate years")]):
            x = i + (k - 0.5) * (w + 0.04)
            v, rv = d.loc["Statewide", col], d.loc[regions, col]
            ax.bar(x, v, width=w, color=c, label=name if i == 0 else None)
            ax.scatter([x] * len(regions), rv, s=12, color=INK, zorder=3,
                       label="Regions (Arctic, Interior, West, South)" if i == 0 and k == 0 else None)
            y = max(v, rv.max()) + 0.07 if v >= 0 else min(v, rv.min()) - 0.07
            ax.text(x, y, f"{v:+.1f}".replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5,
                    color=INK)
    ax.set_xticks(range(len(deps)), [lab for _, lab in deps])
    ax.set_ylabel("GIPL minus ESA (°C), median")
    ax.set_title("GIPL vs ESA CCI, 5-model average RCP 8.5")
    ax.set_ylim(-2.6, 1.9)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "gipl3_bias.png", dpi=200)
    plt.close(fig)


def fig_fingerprint():
    h = pd.read_csv(T7 / "highpass.csv")
    h = h[(h.scen == "rcp45") & (h.region == "Statewide")].set_index("window_km")
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    w = 0.36
    for k, (col, c, name) in enumerate([("partial_gipl_2km_given_771", "#1c5cab", "SNAP 2 km air temperature"),
                                        ("partial_gipl_771_given_2km", "#9ec5f4", "SNAP 771 m air temperature")]):
        xs = np.arange(len(h)) + (k - 0.5) * (w + 0.04)
        ax.bar(xs, h[col], width=w, color=c, label=name)
        for x, v in zip(xs, h[col]):
            ax.text(x, v + 0.01, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_xticks(range(len(h)), [f"{w_} km" for w_ in h.index])
    ax.set_xlabel("Detail finer than (neighbourhood size)")
    ax.set_ylabel("Partial correlation with\nGIPL's fine-scale pattern")
    ax.set_ylim(0, 0.42)
    ax.set_title("Which air temperature map does GIPL's fine detail follow?")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "gipl3_fingerprint.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig_series()
    fig_lagscan()
    fig_bias()
    fig_fingerprint()
    print("figures written", flush=True)
