"""Figures for docs/GIPL_ISSUE_2.md (GIPL start-up period, cold bias, absolute values vs change signal).
Reads <data>/results/t6/ (t6_gipl_levels.py, t6b_sites.py). Writes docs/figures/gipl2_*.png.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Patch

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

T6 = C.DATA / "results/t6"
FIG = C.REPO / "docs/figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
RUN_C = {"5ModelAvg": "#2a78d6", "GFDL-CM3": "#eb6834", "NCAR-CCSM4": "#1baf7a"}
REGION_C = {"Arctic": "#2a78d6", "Interior": "#eb6834", "West": "#1baf7a", "South": "#eda100"}
DEPTH_C = {"magtsurface": "#86b6ef", "magt0.5m": "#3987e5", "magt1m": "#1c5cab", "magt2m": "#0d366b"}
DEP_LABEL = {"magtsurface": "surface", "magt0.5m": "0.5 m", "magt1m": "1 m", "magt2m": "2 m"}
CLASS_C = ["#0072B2", "#F0E442", "#D55E00"]  # team scheme: <= -1 / -1..0 / > 0 degC (PTI 3-tier colours)
CLASS_L = ["≤ −1 °C (good)", "−1 to 0 °C (moderate)", "> 0 °C (bad)"]
PF_C, NOPF_C = "#0d366b", "#e34948"
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                "#7a1d1c"])
DIV.set_bad("#ffffff")
plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 10, "axes.titlelocation": "left"})


def clean(ax, grid="y"):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.6)
        ax.set_axisbelow(True)


def to_grid(values, cols):
    z = np.load(T6 / "cells.npz")
    ny, nx = z["shape"]
    g = np.full(ny * nx, np.nan, "float32")
    g[z["idx"][cols]] = values
    return g.reshape(ny, nx)


def crop(a, min_cells=40):
    """Bounding box of rows / columns with at least min_cells valid cells (drops far-flung islands)."""
    ok = np.isfinite(a)
    r, c = np.flatnonzero(ok.sum(1) >= min_cells), np.flatnonzero(ok.sum(0) >= min_cells)
    return a[r[0]:r[-1] + 1, c[0]:c[-1] + 1]


def fig_startup():
    s = pd.read_csv(T6 / "startup_series.csv")
    s = s[(s.region == "Statewide") & (s.year <= 2050)]
    fig, axs = plt.subplots(2, 4, figsize=(16, 7), sharex=True)
    for j, dep in enumerate(DEP_LABEL):
        for i, scen in enumerate(["rcp45", "rcp85"]):
            ax = axs[i, j]
            ax.axvspan(2000.5, 2015.5, color=GRID, alpha=0.45, lw=0)
            ax.axvspan(2000.5, 2003.5, color=GRID, alpha=0.8, lw=0)
            for run, col in RUN_C.items():
                d = s[(s.run == run) & (s.scen == scen) & (s.depth == dep)]
                ax.plot(d.year, d.gipl_median, color=col, lw=1.6 if run == "5ModelAvg" else 1.2,
                        label=run, zorder=3 if run == "5ModelAvg" else 2)
            ax.set_title(f"{DEP_LABEL[dep]}, RCP {scen[3]}.{scen[4]}")
            clean(ax)
            if j == 0:
                ax.set_ylabel("ground temperature, median (°C)")
    h, l = axs[0, 0].get_legend_handles_labels()
    h += [Patch(color=GRID, alpha=0.9), Patch(color=GRID, alpha=0.45)]
    l += ["2001–2003: start-up years", "2001–2015: observed weather (CRU), same in every run"]
    fig.legend(h, l, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.03))
    for ax in axs[-1]:
        ax.set_xlabel("climate year (GIPL file year − 20)")
    fig.tight_layout()
    fig.savefig(FIG / "gipl2_startup.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_gap():
    g = pd.read_csv(T6 / "startup_gap.csv")
    g = g[g.year <= 2050]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for dep, col in DEPTH_C.items():
        d = g[g.depth == dep]
        ax.plot(d.year, d.gipl_gap, color=col, lw=1.8, marker="o", ms=3.5, label=f"GIPL {DEP_LABEL[dep]}")
    d = g[g.depth == "magtsurface"]
    ax.plot(d.year, d.air_gap, color=INK2, lw=1.2, ls=(0, (3, 2)),
            label="air temperature (observed to 2015, the same in both; then 5-model average)")
    ax.axvspan(2000.5, 2003.5, color=GRID, lw=0)
    ax.set_xlabel("climate year (GIPL file year − 20)")
    ax.set_ylabel("median |RCP 8.5 − RCP 4.5| (°C)")
    ax.set_title("How far apart the two scenarios are, year by year (5ModelAvg)")
    ax.legend(frameon=False, fontsize=8.5)
    clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "gipl2_scenario_gap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_bias():
    b = pd.read_csv(T6 / "bias.csv")
    b = b[(b.scen == "rcp85") & (b.years == "2004-2015")]
    deps = ["magtsurface", "magt1m", "magt2m"]
    regs = ["Statewide", "Arctic", "Interior", "West", "South"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    w = 0.15
    for i, dep in enumerate(deps):
        for k, rn in enumerate(regs):
            r = b[(b.run == "5ModelAvg") & (b.depth == dep) & (b.region == rn)].iloc[0]
            x = i + (k - 2) * w
            col = INK if rn == "Statewide" else REGION_C[rn]
            ax.plot([x, x], [r.offset_p10, r.offset_p90], color=col, lw=1.2, solid_capstyle="round")
            ax.plot([x, x], [r.offset_p25, r.offset_p75], color=col, lw=5, solid_capstyle="round")
            ax.plot(x, r.offset_median, "o", color="white", ms=4.5, mec=col, mew=1.5, zorder=3)
        for run, mk in [("GFDL-CM3", "^"), ("NCAR-CCSM4", "s")]:
            r = b[(b.run == run) & (b.depth == dep) & (b.region == "Statewide")].iloc[0]
            ax.plot(i - 2 * w - 0.07, r.offset_median, mk, color=RUN_C[run], ms=5)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(3), ["surface (vs ESA GST)", "1 m (vs ESA T1m)", "2 m (vs ESA T2m)"])
    ax.set_ylabel("GIPL − ESA, same years (°C)")
    ax.set_title("GIPL vs ESA, both 2004–2015 (observed weather in both), cell by cell: median (dot), middle half (bar), "
                 "10th–90th percentile (line)")
    h = [plt.Line2D([], [], color=INK if r == "Statewide" else REGION_C[r], lw=5) for r in regs]
    h += [plt.Line2D([], [], ls="", marker="^", color=RUN_C["GFDL-CM3"]),
          plt.Line2D([], [], ls="", marker="s", color=RUN_C["NCAR-CCSM4"])]
    ax.legend(h, regs + ["GFDL-CM3 run, statewide median", "NCAR-CCSM4 run, statewide median"], frameon=False,
              fontsize=8, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.32))
    clean(ax)
    fig.savefig(FIG / "gipl2_bias_depth.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_bias_maps():
    z = np.load(T6 / "grids_bias.npz")
    cols = z["cols"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), gridspec_kw=dict(wspace=0.02))
    for ax, dep in zip(axs, ["magtsurface", "magt1m", "magt2m"]):
        g = crop(to_grid(z[f"offset_rcp85_{dep}_2004"], cols))
        im = ax.imshow(g, cmap=DIV, vmin=-4, vmax=4, interpolation="nearest")
        ax.set_title(DEP_LABEL[dep])
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    fig.colorbar(im, ax=axs, shrink=0.8, pad=0.01, label="GIPL − ESA, both 2004–2015 (°C); blue = GIPL colder")
    fig.savefig(FIG / "gipl2_bias_maps.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_boreholes():
    d = pd.read_csv(T6 / "borehole_compare.csv")
    d = d[d.gipl_class.isin([1, 2]) & d.esa.notna() & d.gipl.notna()]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, (k, lab) in zip(axs, [("sfc", "surface"), ("d1m", "1 m"), ("d2m", "2 m")]):
        g = d[d.depth == k]
        lim = (-8, 5)
        ax.plot(lim, lim, color=INK2, lw=0.8, ls=(0, (2, 2)))
        ax.scatter(g.obs, g.esa, s=22, color="#9a9890", edgecolor="white", lw=0.5, label="ESA CCI", zorder=2)
        ax.scatter(g.obs, g.gipl, s=22, color=RUN_C["5ModelAvg"], edgecolor="white", lw=0.5,
                   label="GIPL (5ModelAvg)", zorder=3)
        e1, e2 = np.median(g.esa - g.obs), np.median(g.gipl - g.obs)
        ax.set_title(f"{lab}: {len(g)} sites — median error ESA {e1:+.1f} °C, GIPL {e2:+.1f} °C")
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel("observed mean annual temperature (°C)")
        clean(ax, grid="both")
    axs[0].set_ylabel("dataset value for the site's 1 km cell (°C)")
    axs[0].legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG / "gipl2_boreholes.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_cusp():
    d = pd.read_csv(T6 / "cusp_compare.csv")
    sk = pd.read_csv(T6 / "cusp_skill.csv").set_index("predictor")
    preds = [c for c in sk.index if not c.startswith("esa_pfr")]
    d = d[d.gipl_class.isin([1, 2]) & d[preds].notna().all(axis=1) & d.esa_pfr.notna()]
    fig, axs = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    bins = np.arange(-8, 6.01, 0.25)
    for i, (k, lab) in enumerate([("sfc", "surface"), ("d1m", "1 m")]):
        for j, (p, name) in enumerate([(f"esa_{k}", "ESA CCI"), (f"gipl_{k}", "GIPL (5ModelAvg)")]):
            ax = axs[i, j]
            for v, col, ll in [(1, PF_C, "permafrost found"), (0, NOPF_C, "no permafrost found")]:
                x = np.clip(d.loc[d.pf_obs == v, p].values, -8, 6)
                ax.hist(x, bins=bins, weights=np.full(x.size, 100 / x.size), histtype="step", lw=1.8, color=col,
                        label=f"{ll} ({x.size} cells)")
            r = sk.loc[p]
            ax.axvline(0, color=INK, lw=1)
            ax.axvline(r.best_threshold, color=INK2, lw=1, ls=(0, (3, 2)))
            ax.text(r.best_threshold, ax.get_ylim()[1] * 0.97, f" best split {r.best_threshold:+.1f} °C",
                    color=INK2, fontsize=8.5, va="top", bbox=dict(fc="white", ec="none", pad=1))
            ax.set_title(f"{name}, {lab}")
            ax.text(0.02, 0.96, f"Split at 0 °C:\n{100 * r.miss_rate_0C:.0f} % of permafrost cells read thawed\n"
                    f"{100 * r.false_frozen_0C:.0f} % of no-permafrost cells read frozen", transform=ax.transAxes,
                    va="top", fontsize=8.5, color=INK)
            clean(ax)
            if j == 0:
                ax.set_ylabel("% of cells")
            if i == 1:
                ax.set_xlabel("mean annual temperature (°C), CUSP observation years")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout()
    fig.savefig(FIG / "gipl2_cusp.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_classes():
    c = pd.read_csv(T6 / "classes_mid.csv")
    z = np.load(T6 / "grids.npz")
    cols = z["cols"]
    cmap = ListedColormap(CLASS_C)
    cmap.set_bad("#ffffff")
    fig = plt.figure(figsize=(17, 5.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.75], wspace=0.08)
    for j, (key, ttl) in enumerate([("mid_raw_rcp85_magt1m", "Raw GIPL, 1 m"),
                                    ("mid_adj_rcp85_magt1m", "ESA-adjusted (delta change), 1 m")]):
        ax = fig.add_subplot(gs[j])
        v = z[key]
        cl = np.digitize(v, (-1.0, 0.0), right=True).astype("float32")
        cl[~np.isfinite(v)] = np.nan
        ax.imshow(crop(to_grid(cl, cols)), cmap=cmap, vmin=-0.5, vmax=2.5, interpolation="nearest")
        ax.set_title(ttl)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    ax = fig.add_subplot(gs[2])
    ax.set_position(ax.get_position().translated(0.05, 0))
    st = c[(c.region == "Statewide") & (c.scen == "rcp85")].set_index("depth")
    bars = []
    for dep in ["magtsurface", "magt0.5m", "magt1m", "magt2m"]:
        bars.append((f"{DEP_LABEL[dep]} raw", [st.loc[dep, f"raw_{i}"] for i in range(3)]))
        if dep != "magt0.5m":
            bars.append((f"{DEP_LABEL[dep]} adjusted", [st.loc[dep, f"adj_{i}"] for i in range(3)]))
    y = np.arange(len(bars))[::-1]
    for yy, (lab, sh) in zip(y, bars):
        left = 0
        for i, v in enumerate(sh):
            ax.barh(yy, 100 * v, left=left, color=CLASS_C[i], height=0.7, edgecolor="white", lw=1)
            if v > 0.08:
                ax.text(left + 50 * v, yy, f"{100 * v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if i != 1 else INK)
            left += 100 * v
    ax.set_yticks(y, [b[0] for b in bars])
    ax.set_xlabel("% of permafrost cells")
    ax.set_title("Class shares by depth (statewide)")
    ax.set_xlim(0, 100)
    clean(ax, grid=None)
    fig.suptitle("Team scheme at mid-century (2051–2080, RCP 8.5)", x=0.125, ha="left", y=1.0, fontsize=11)
    fig.legend([Patch(color=c_) for c_ in CLASS_C], CLASS_L, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.45, -0.04))
    fig.savefig(FIG / "gipl2_classes_mid.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_pileup():
    z = np.load(T6 / "grids.npz")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.arange(-8, 6.01, 0.2)
    ax.axvspan(-1, 0, color=CLASS_C[1], alpha=0.25, lw=0)
    for dep, col in DEPTH_C.items():
        v = z[f"mid_raw_rcp85_{dep}"]
        v = np.clip(v[np.isfinite(v)], -8, 6)
        ax.hist(v, bins=bins, weights=np.full(v.size, 100 / v.size), histtype="step", lw=1.8, color=col,
                label=DEP_LABEL[dep])
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("raw GIPL mean annual temperature, 2051–2080, RCP 8.5 (°C)")
    ax.set_ylabel("% of permafrost cells")
    ax.set_title("Below the surface, GIPL values pile up just under 0 °C (shaded: the −1 to 0 °C class)")
    ax.legend(frameon=False, title="depth", fontsize=8.5)
    clean(ax)
    fig.tight_layout()
    fig.savefig(FIG / "gipl2_pileup.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for f in [fig_startup, fig_gap, fig_bias, fig_bias_maps, fig_boreholes, fig_cusp, fig_classes, fig_pileup]:
        f()
        print(f.__name__, flush=True)
