"""Figures for docs/GIPL_TRUST.pdf (two-page summary: can GIPL 2.0 be trusted?).
Reads <data>/results/t6/ (t6_gipl_levels.py, t6b_sites.py) and t7/ (t7_gipl_forcing.py). GIPL is drawn on climate
years (file year - 20, GIPL_ISSUE_3.md). Writes docs/figures/gipl_trust_*.pdf at print size (7.3 in wide), so font
sizes are the sizes on the page.
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
T7 = C.DATA / "results/t7"
FIG = C.REPO / "docs/figures"
W = 7.3  # figure width = text width on the page (in)
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
ESA_C = "#9a9890"
STUCK_C, BORDER_C, PF_C, LAND_C = "#c2410c", "#f4b393", "#cfcdc6", "#efeeea"
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                "#7a1d1c"])
DIV.set_bad((0, 0, 0, 0))
STUCK_RC = (682, 1302)  # Fairbanks test-area centre cell (65.05N 147.14W), as in GIPL_ISSUE_1.md
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 7.5, "axes.titlesize": 8,
                     "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5,
                     "ytick.major.size": 2.5, "legend.fontsize": 7, "pdf.fonttype": 42})


def clean(ax, grid="y"):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.5)
        ax.set_axisbelow(True)


def no_frame(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


CELLS = np.load(T6 / "cells.npz")
NY, NX = CELLS["shape"]


def to_grid(values, cols=slice(None)):
    g = np.full(NY * NX, np.nan, "float32")
    g[CELLS["idx"][cols]] = values
    return g.reshape(NY, NX)


def pf_box(pad=15):
    """Rows / columns spanning the permafrost cells (classes 2-4): mainland Alaska north of ~60 N."""
    cls = to_grid(CELLS["cls"].astype("float32"))
    pf = cls >= 2
    r, c = np.flatnonzero(pf.sum(1) >= 20), np.flatnonzero(pf.sum(0) >= 20)
    return slice(max(r[0] - pad, 0), r[-1] + pad), slice(max(c[0] - pad, 0), c[-1] + pad)


def base_map(ax, box):
    """Land in light grey, permafrost cells in mid grey (cell classes from the stuck-cell mask)."""
    cls = to_grid(CELLS["cls"].astype("float32"))[box]
    base = np.where(np.isfinite(cls), np.where(cls >= 2, 1.0, 0.0), np.nan)
    ax.imshow(base, cmap=ListedColormap([LAND_C, PF_C]), vmin=0, vmax=1, interpolation="nearest")
    return cls


def stack(name):
    return np.load(T6 / f"{name}.npy", mmap_mode="r")


def fig_years():
    """GFDL-CM3 RCP 4.5, statewide median: GIPL surface year-to-year changes next to air temperature, as labelled and
    shifted by 20 years (t7 series.csv; per-cell match from t7 offsets.csv)."""
    sr = pd.read_csv(T7 / "series.csv")
    d = sr[(sr.run == "GFDL-CM3") & (sr.scen == "rcp45")].set_index("gipl_year")
    off = pd.read_csv(T7 / "offsets.csv")
    off = off[(off.run == "GFDL-CM3") & (off.scen == "rcp45") & (off.depth == "magtsurface")
              & (off.air == "2k_GFDL-CM3_rcp45")].set_index("offset").median_r
    g = d.gipl_surface.diff()
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.5), sharey=True,
                            gridspec_kw=dict(wspace=0.08, left=0.07, right=0.995, bottom=0.24, top=0.8))
    same = d.model_air_same_year.diff()
    shifted = d.model_air_shifted.diff().where(d.forcing_year >= 2017)
    obs = d.cru_air.diff().where((d.forcing_year >= 2005) & (d.forcing_year <= 2015))
    gi = g[g.index >= 2024]
    ax = axs[0]
    ax.axhline(0, color=INK2, lw=0.6)
    ax.plot(same.index, same, color=MUTED, lw=0.9)
    ax.plot(gi.index, gi, color=ORANGE, lw=1.1)
    ax.set_xlim(2023, 2100)
    ax.set_xticks([2030, 2050, 2070, 2090])
    ax.set_xlabel("year in the file name")
    ax.set_ylabel("change from previous year (°C)")
    ax.set_title(f"a. As labelled: no match (r = {off.loc[0]:.2f})", pad=3)
    clean(ax)
    ax = axs[1]
    ax.axhline(0, color=INK2, lw=0.6)
    ax.plot(obs.index - 20, obs, color=MUTED, lw=0.9, ls=(0, (2.5, 1.5)))
    ax.plot(shifted.index - 20, shifted, color=MUTED, lw=0.9)
    ax.plot(gi.index - 20, gi, color=ORANGE, lw=1.1)
    ax.set_xlim(2003, 2080)
    ax.set_xticks([2010, 2030, 2050, 2070])
    ax.set_xlabel("year in the file name − 20")
    ax.set_title(f"b. Shifted 20 years: match (r = {off.loc[20]:.2f})", pad=3)
    fig.legend([plt.Line2D([], [], color=ORANGE, lw=1.1), plt.Line2D([], [], color=MUTED, lw=0.9),
                plt.Line2D([], [], color=MUTED, lw=0.9, ls=(0, (2.5, 1.5)))],
               ["GIPL ground surface", "air, GFDL-CM3 RCP 4.5 (projected)", "air, observed"], loc="upper right",
               bbox_to_anchor=(0.995, 1.04), frameon=False, fontsize=6.5, ncol=3, handlelength=1.4, columnspacing=1.2)
    clean(ax)
    fig.savefig(FIG / "gipl_trust_1_years.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_stuck():
    box = pf_box()
    fig = plt.figure(figsize=(W, 1.95))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1, 1], wspace=0.28, left=0.0, right=0.99, bottom=0.17, top=0.86)
    ax = fig.add_subplot(gs[0])
    cls = base_map(ax, box)
    over = np.where(cls == 4, 1.0, np.where(cls == 3, 0.0, np.nan))
    ax.imshow(over, cmap=ListedColormap([BORDER_C, STUCK_C]), vmin=0, vmax=1, interpolation="nearest")
    r0, c0 = STUCK_RC[0] - box[0].start, STUCK_RC[1] - box[1].start
    ax.plot(c0, r0, "o", ms=5, mfc="none", mec=INK, mew=1.0)
    ax.annotate("cell shown\nat right", xy=(c0, r0), xytext=(-5, 5), textcoords="offset points", fontsize=6.5,
                color=INK, ha="right", va="bottom")
    no_frame(ax)
    ax.set_title("a. Where it happens", pad=3)
    ax.legend([Patch(color=STUCK_C), Patch(color=BORDER_C), Patch(color=PF_C)],
              ["stuck (46,000 km²)", "within 2 km of a stuck cell", "other permafrost"],
              loc="lower left", frameon=False, fontsize=6.5, handlelength=1.2, borderaxespad=0.2)

    # one stuck cell vs the nearest normal permafrost cell > 2 km away; 5-model average, RCP 8.5, climate years
    cgrid = to_grid(CELLS["cls"].astype("float32"))
    r, c = STUCK_RC
    win = cgrid[r - 15:r + 16, c - 15:c + 16]
    rr, cc = np.nonzero(win == 2)
    d = np.hypot(rr - 15, cc - 15)
    d[d <= 2] = np.inf
    k = np.argmin(d)
    nb = (r - 15 + rr[k], c - 15 + cc[k])
    kk = [int(np.flatnonzero(CELLS["idx"] == rc[0] * NX + rc[1])[0]) for rc in (STUCK_RC, nb)]
    yrs = np.arange(C.GIPL_START_OK, 2101)  # climate years; file row = year + 20 - 2021
    rows = yrs + 20 - 2021
    sfc, d1m = stack("gipl_5ModelAvg_rcp85_magtsurface"), stack("gipl_5ModelAvg_rcp85_magt1m")
    cru, mod = stack("maat_cru"), stack("maat_rcp85")  # 2000-2023, 2006-2100
    km = np.hypot(*(np.subtract(nb, STUCK_RC))) * 1.0
    axs = [fig.add_subplot(gs[1]), None]
    axs[1] = fig.add_subplot(gs[2], sharey=axs[0])
    for ax, k_, ttl in zip(axs, kk, ["b. A stuck cell near Fairbanks", f"c. Normal cell {km:.0f} km away"]):
        air = [float(cru[y - 2000, k_]) if y <= 2015 else float(mod[y - 2006, k_]) for y in yrs]
        ax.plot(yrs, air, color=MUTED, lw=0.9, label="air")
        ax.plot(yrs, np.asarray(sfc[rows, k_], "float32"), color=ORANGE, lw=1.2, label="ground surface")
        ax.plot(yrs, np.asarray(d1m[rows, k_], "float32"), color=BLUE, lw=1.4, label="1 m below ground")
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_title(ttl, pad=3)
        ax.set_xlim(2003, 2101)
        ax.set_xticks([2010, 2040, 2070, 2100])
        clean(ax)
    axs[0].set_ylabel("mean annual temperature (°C)")
    axs[0].set_yticks(range(-2, 9, 2))
    plt.setp(axs[1].get_yticklabels(), visible=False)
    h, l = axs[0].get_legend_handles_labels()
    axs[0].legend([h[1], h[0], h[2]], [l[1], l[0], l[2]], loc="upper left", frameon=False, fontsize=6.5,
                  handlelength=1.2, borderaxespad=0.1)
    v0 = float(d1m[rows[0], kk[0]])
    axs[0].text(2098, v0 + 0.35, f"{v0:.1f} °C every year".replace("-", "−"), fontsize=6.5, color=INK, ha="right",
                va="bottom")
    fig.savefig(FIG / "gipl_trust_2_stuck.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("stuck", STUCK_RC, "neighbour", nb, f"{km:.1f} km")


def fig_levels():
    box = pf_box()
    fig = plt.figure(figsize=(W, 1.95))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.34, left=0.0, right=0.99, bottom=0.21, top=0.855)
    ax = fig.add_subplot(gs[0])
    base_map(ax, box)
    z = np.load(T6 / "grids_bias.npz")
    g = to_grid(z["offset_rcp85_magt1m_2004"], z["cols"])[box]
    im = ax.imshow(g, cmap=DIV, vmin=-4, vmax=4, interpolation="nearest")
    no_frame(ax)
    ax.set_title("a. GIPL minus ESA CCI, 1 m, 2004–2015", pad=3)
    cax = ax.inset_axes([1.03, 0.12, 0.035, 0.62])
    cb = fig.colorbar(im, cax=cax, ticks=[-4, -2, 0, 2, 4])
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6, length=1.5, pad=1)
    cax.set_title("°C", fontsize=6, loc="left", pad=3, fontweight="normal", color=INK2)
    ax.text(0.02, 0.02, "blue: GIPL colder\nred: GIPL warmer", transform=ax.transAxes, fontsize=6.5, color=INK2)

    ax = fig.add_subplot(gs[1])
    d = pd.read_csv(T6 / "borehole_compare.csv")
    d = d[d.gipl_class.isin([1, 2]) & d.esa.notna() & d.gipl.notna() & (d.depth == "d1m")]
    lim = (-8, 4)
    ax.plot(lim, lim, color=INK2, lw=0.7)
    ax.scatter(d.obs, d.esa, s=11, color=ESA_C, edgecolor="white", lw=0.4, zorder=2)
    ax.scatter(d.obs, d.gipl, s=11, color=BLUE, edgecolor="white", lw=0.4, zorder=3)
    e_esa, e_gipl = np.median(d.esa - d.obs), np.median(d.gipl - d.obs)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xticks([-8, -4, 0, 4]); ax.set_yticks([-8, -4, 0, 4])
    ax.set_xlabel("measured in borehole (°C)")
    ax.set_ylabel("dataset value (°C)")
    ax.set_title(f"b. {len(d)} boreholes, 1 m, same years", pad=3)
    ax.legend([plt.Line2D([], [], ls="", marker="o", ms=4, color=c) for c in (BLUE, ESA_C)]
              + [plt.Line2D([], [], color=INK2, lw=0.7)],
              [f"GIPL (median {e_gipl:+.1f} °C)".replace("-", "−"), f"ESA CCI ({e_esa:+.1f} °C)".replace("-", "−"),
               "perfect match"],
              loc="upper left", frameon=False, fontsize=6.5, handletextpad=0.2, borderaxespad=0.2)
    clean(ax, grid="both")

    ax = fig.add_subplot(gs[2])
    c = pd.read_csv(T6 / "cusp_compare.csv")
    c = c[c.gipl_class.isin([1, 2]) & c.gipl_d1m.notna() & c.esa_d1m.notna()]
    bins = np.arange(-8, 6.01, 0.5)
    h, l = [], []
    for v, col, name in [(1, "#0d366b", "permafrost found"), (0, "#e34948", "none found")]:
        x = np.clip(c.loc[c.pf_obs == v, "gipl_d1m"].values, -7.99, 5.99)
        ax.hist(x, bins=bins, weights=np.full(x.size, 100 / x.size), histtype="step", lw=1.3, color=col)
        h.append(plt.Line2D([], [], color=col, lw=1.3))
        share = (x <= 0).mean() if v == 1 else (x > 0).mean()
        l.append(f"{name}:\n{100 * share:.0f} % {'below' if v == 1 else 'above'} 0 °C")
    ax.axvline(0, color=INK2, lw=0.6)
    top = ax.get_ylim()[1]
    ax.set_ylim(0, top * 1.75)
    ax.legend(h, l, loc="upper left", frameon=False, fontsize=6.3, handlelength=1.0, handletextpad=0.4,
              labelspacing=0.5, borderaxespad=0.1, ncol=2, columnspacing=0.8)
    ax.set_xlim(-8, 6)
    ax.set_xticks([-8, -4, 0, 4])
    ax.set_xlabel("GIPL temperature at 1 m (°C)")
    ax.set_ylabel("% of sites")
    ax.set_title(f"c. {len(c):,} field sites (CUSP)", pad=3)
    clean(ax)
    fig.savefig(FIG / "gipl_trust_3_levels.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("boreholes 1 m", len(d), f"GIPL {e_gipl:+.2f} ESA {e_esa:+.2f}", "CUSP cells", len(c))


def fig_runs():
    """Half width. a: start-up at 1 m (5-model average, both scenarios), climate years. b: NCAR-CCSM4's 2003 surface
    spike against the 5-model average (thick pale line)."""
    s = pd.read_csv(T6 / "startup_series.csv")
    s = s[(s.region == "Statewide") & (s.year <= 2025)]
    fig, axs = plt.subplots(1, 2, figsize=(3.55, 1.75), gridspec_kw=dict(wspace=0.36, left=0.15, right=0.99,
                                                                          bottom=0.19, top=0.85))
    ax = axs[0]
    ax.axvspan(2000.5, 2003.5, color=GRID, lw=0)
    ax.text(2002, 0.97, "start-\nup", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6,
            color=INK2)
    for scen, col, lab in [("rcp45", BLUE, "RCP 4.5"), ("rcp85", ORANGE, "RCP 8.5")]:
        d = s[(s.run == "5ModelAvg") & (s.scen == scen) & (s.depth == "magt1m")]
        ax.plot(d.year, d.gipl_median, color=col, lw=1.2, label=lab)
    ax.set_title("a. 1 m, 5-model avg.", pad=3)
    ax.set_ylabel("median temperature (°C)")
    ax.legend(frameon=False, loc="lower right", fontsize=6, handlelength=1.0)
    ax.set_xlim(2000.5, 2025.5)
    ax.set_xticks([2005, 2015, 2025])
    clean(ax)
    ax = axs[1]
    o = s[(s.run == "5ModelAvg") & (s.scen == "rcp45") & (s.depth == "magtsurface") & (s.year <= 2015)]
    ax.plot(o.year, o.gipl_median, color=PF_C, lw=3.0, solid_capstyle="round", zorder=1, label="other runs")
    for scen, col in [("rcp45", BLUE), ("rcp85", ORANGE)]:
        d = s[(s.run == "NCAR-CCSM4") & (s.scen == scen) & (s.depth == "magtsurface") & (s.year <= 2015)]
        ax.plot(d.year, d.gipl_median, color=col, lw=1.1, zorder=3, label=f"NCAR {scen[3]}.{scen[4]}")
    ax.set_title("b. Surface, NCAR-CCSM4", pad=3)
    ax.legend(frameon=False, loc="upper right", fontsize=6, handlelength=1.0, borderaxespad=0.1)
    ax.set_xlim(2000.5, 2015.5)
    ax.set_xticks([2003, 2009, 2015])
    clean(ax)
    fig.savefig(FIG / "gipl_trust_4_runs.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def stats():
    """Numbers quoted in the text but not drawn: stuck share by region (of the ESA PFR > 0 2020 domain, as in
    GIPL_ISSUE_1.md) and the century range by depth in stuck vs normal permafrost cells (5-model average, RCP 8.5;
    3 and 5 m from the source GeoTIFFs at a 3,000-cell sample). Writes <data>/results/t6/trust_stats.csv."""
    import rasterio
    sys.path.insert(0, str(C.REPO / "scripts/02_tests"))
    from t3c_gipl_statewide import esa_pfr_on_grid
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg = s.read(1)
    pfr = esa_pfr_on_grid(prof)
    pf = (cls > 0) & (pfr > 0) & (pfr <= 100)
    rows = []
    for r, name in [(0, "Statewide"), (1, "Arctic"), (2, "Interior"), (3, "West"), (4, "South")]:
        m = np.ones_like(pf) if r == 0 else reg == r
        rows += [dict(stat="stuck share of ESA PFR>0 (2020)", group=name,
                      value=((cls == 4) & m & pf).sum() / (m & pf).sum()),
                 dict(stat="stuck + 2 km border share of ESA PFR>0 (2020)", group=name,
                      value=((cls >= 3) & m & pf).sum() / (m & pf).sum()),
                 dict(stat="share of all stuck cells", group=name, value=((cls == 4) & m).sum() / (cls == 4).sum())]

    stuck = np.flatnonzero(CELLS["cls"] == 4)
    normal = np.flatnonzero((CELLS["cls"] == 2) & (CELLS["pfr_2023"] > 0))
    for dep in ["magtsurface", "magt0.5m", "magt1m", "magt2m"]:
        a = stack(f"gipl_5ModelAvg_rcp85_{dep}")
        for name, k in [("stuck", stuck), ("normal", normal[::5])]:
            v = np.asarray(a[:, k], "float32")
            rows.append(dict(stat=f"median 2021-2120 range, {dep}", group=name, value=np.median(v.max(0) - v.min(0))))
    rng = np.random.default_rng(0)
    sample = {"stuck": CELLS["idx"][rng.choice(stuck, 3000, replace=False)],
              "normal": CELLS["idx"][rng.choice(normal, 3000, replace=False)]}
    for dep in ["magt3m", "magt5m"]:
        v = {k: [] for k in sample}
        for y in range(2021, 2121):
            with rasterio.open(C.DATA / f"gipl_tif/{dep}/gipl_5ModelAvg_rcp85_{dep}_degC_{y}.tif") as s:
                a = s.read(1).ravel()
            for k, i in sample.items():
                v[k].append(a[i])
        for k in sample:
            x = np.array(v[k], "float32")
            x[x < -9000] = np.nan
            rows.append(dict(stat=f"median 2021-2120 range, {dep} (3,000-cell sample)", group=k,
                             value=np.nanmedian(np.nanmax(x, 0) - np.nanmin(x, 0))))

    # shared starting maps (2021) and GFDL-CM3 RCP 8.5 one year ahead of the 5-model average RCP 8.5
    ref = {d: np.asarray(stack(f"gipl_5ModelAvg_rcp45_{d}")[0], "float32") for d in ["magtsurface", "magt1m"]}
    for run in ["GFDL-CM3_rcp45", "NCAR-CCSM4_rcp45", "NCAR-CCSM4_rcp85", "5ModelAvg_rcp85", "GFDL-CM3_rcp85"]:
        for dep, r in ref.items():
            a = np.asarray(stack(f"gipl_{run}_{dep}")[0], "float32")
            ok = np.isfinite(a) & np.isfinite(r)
            rows.append(dict(stat=f"2021 {dep} identical to 5ModelAvg rcp45, share of cells", group=run,
                             value=(a[ok] == r[ok]).mean()))
    s = pd.read_csv(T6 / "startup_series.csv")
    s = s[(s.region == "Statewide") & (s.depth == "magtsurface")].pivot_table(index="year", columns=["run", "scen"],
                                                                                values="gipl_median")
    gap = (s[("5ModelAvg", "rcp85")] - s[("GFDL-CM3", "rcp85")].shift(1)).abs()
    rows += [dict(stat="|5ModelAvg rcp85 - GFDL-CM3 rcp85 one year earlier|, statewide surface median, max",
                  group=f"{y0}-{y1}", value=gap.loc[y0:y1].max()) for y0, y1 in [(2022, 2022), (2023, 2035)]]
    a, g = stack("gipl_5ModelAvg_rcp85_magtsurface"), stack("gipl_GFDL-CM3_rcp85_magtsurface")
    for y0, y1 in [(2023, 2035), (2036, 2036)]:
        d = np.abs(np.asarray(a[y0 - 2021:y1 - 2020][:, normal], "float32")
                   - np.asarray(g[y0 - 2022:y1 - 2021][:, normal], "float32"))
        rows += [dict(stat=f"|5ModelAvg rcp85 - GFDL-CM3 rcp85 one year earlier|, surface, per cell, {q}",
                      group=f"{y0}-{y1}", value=np.percentile(d, p)) for q, p in [("median", 50), ("p90", 90)]]
    df = pd.DataFrame(rows)
    df.to_csv(T6 / "trust_stats.csv", index=False)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    if "--stats" in sys.argv:
        stats()
    else:
        for f in [fig_years, fig_stuck, fig_levels, fig_runs]:
            f()
            print(f.__name__, flush=True)
