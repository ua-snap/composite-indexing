"""Figures for docs/GIPL_TRUST.pdf (two-page summary: can GIPL 2.0 be trusted?).
Reads <data>/results/t6/ (t6_gipl_levels.py, t6b_sites.py). Writes docs/figures/gipl_trust_*.pdf at print size
(7.3 in wide), so font sizes are the sizes on the page.
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


def fig_stuck():
    box = pf_box()
    fig = plt.figure(figsize=(W, 2.17))
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

    # one stuck cell vs the nearest normal permafrost cell > 2 km away; 5-model average, RCP 8.5
    cgrid = to_grid(CELLS["cls"].astype("float32"))
    r, c = STUCK_RC
    win = cgrid[r - 15:r + 16, c - 15:c + 16]
    rr, cc = np.nonzero(win == 2)
    d = np.hypot(rr - 15, cc - 15)
    d[d <= 2] = np.inf
    k = np.argmin(d)
    nb = (r - 15 + rr[k], c - 15 + cc[k])
    kk = [int(np.flatnonzero(CELLS["idx"] == rc[0] * NX + rc[1])[0]) for rc in (STUCK_RC, nb)]
    yrs, myrs = np.arange(2021, 2121), np.arange(2006, 2101)
    sfc, d1m, air = stack("gipl_5ModelAvg_rcp85_magtsurface"), stack("gipl_5ModelAvg_rcp85_magt1m"), stack("maat_rcp85")
    km = np.hypot(*(np.subtract(nb, STUCK_RC))) * 1.0
    axs = [fig.add_subplot(gs[1]), None]
    axs[1] = fig.add_subplot(gs[2], sharey=axs[0])
    g80 = slice(0, 80)  # 2021-2100, the years with air temperature
    for ax, k_, ttl in zip(axs, kk, ["b. A stuck cell near Fairbanks", f"c. Normal cell {km:.0f} km away"]):
        ax.plot(myrs[15:], np.asarray(air[15:, k_], "float32"), color=MUTED, lw=0.9, label="air")
        ax.plot(yrs[g80], np.asarray(sfc[g80, k_], "float32"), color=ORANGE, lw=1.2, label="ground surface")
        ax.plot(yrs[g80], np.asarray(d1m[g80, k_], "float32"), color=BLUE, lw=1.4, label="1 m below ground")
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_title(ttl, pad=3)
        ax.set_xlim(2020, 2101)
        ax.set_xticks([2025, 2050, 2075, 2100])
        clean(ax)
    axs[0].set_ylabel("mean annual temperature (°C)")
    plt.setp(axs[1].get_yticklabels(), visible=False)
    h, l = axs[0].get_legend_handles_labels()
    axs[0].legend([h[1], h[0], h[2]], [l[1], l[0], l[2]], loc="upper left", frameon=False, fontsize=6.5,
                  handlelength=1.2, borderaxespad=0.1)
    axs[0].text(2098, float(d1m[0, kk[0]]) + 0.35, f"{float(d1m[0, kk[0]]):.1f} °C every year".replace("-", "−"),
                fontsize=6.5, color=INK, ha="right", va="bottom")
    fig.savefig(FIG / "gipl_trust_1_stuck.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("stuck", STUCK_RC, "neighbour", nb, f"{km:.1f} km")


def fig_cold():
    box = pf_box()
    fig = plt.figure(figsize=(W, 2.12))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.34, left=0.0, right=0.99, bottom=0.21, top=0.855)
    ax = fig.add_subplot(gs[0])
    base_map(ax, box)
    z = np.load(T6 / "grids_bias.npz")
    g = to_grid(z["excess_rcp85_magt1m_2026"], z["cols"])[box]
    im = ax.imshow(g, cmap=DIV, vmin=-4, vmax=4, interpolation="nearest")
    no_frame(ax)
    ax.set_title("a. GIPL minus ESA CCI, 1 m", pad=3)
    cax = ax.inset_axes([1.03, 0.12, 0.035, 0.62])
    cb = fig.colorbar(im, cax=cax, ticks=[-4, -2, 0, 2, 4])
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6, length=1.5, pad=1)
    cax.set_title("°C", fontsize=6, loc="left", pad=3, fontweight="normal", color=INK2)
    ax.text(0.02, 0.02, "blue: GIPL colder\nred: GIPL warmer", transform=ax.transAxes, fontsize=6.5, color=INK2)

    ax = fig.add_subplot(gs[1])
    d = pd.read_csv(T6 / "borehole_compare.csv")
    d = d[d.gipl_class.isin([1, 2]) & d.esa.notna() & d.gipl_implied.notna() & (d.depth == "d1m")]
    lim = (-8, 4)
    ax.plot(lim, lim, color=INK2, lw=0.7)
    ax.text(3.6, -7.6, "below the line:\ntoo cold", fontsize=6, color=INK2, ha="right", va="bottom")
    ax.scatter(d.obs, d.esa, s=11, color=ESA_C, edgecolor="white", lw=0.4, zorder=2)
    ax.scatter(d.obs, d.gipl_implied, s=11, color=BLUE, edgecolor="white", lw=0.4, zorder=3)
    e_esa, e_gipl = np.median(d.esa - d.obs), np.median(d.gipl_implied - d.obs)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xticks([-8, -4, 0, 4]); ax.set_yticks([-8, -4, 0, 4])
    ax.set_xlabel("measured in borehole (°C)")
    ax.set_ylabel("dataset value (°C)")
    ax.set_title(f"b. {len(d)} boreholes, 1 m", pad=3)
    ax.legend([plt.Line2D([], [], ls="", marker="o", ms=4, color=c) for c in (BLUE, ESA_C)]
              + [plt.Line2D([], [], color=INK2, lw=0.7)],
              [f"GIPL (median {e_gipl:+.1f} °C)".replace("-", "−"), f"ESA CCI ({e_esa:+.1f} °C)".replace("-", "−"),
               "perfect match"],
              loc="upper left", frameon=False, fontsize=6.5, handletextpad=0.2, borderaxespad=0.2)
    clean(ax, grid="both")

    ax = fig.add_subplot(gs[2])
    sk = pd.read_csv(T6 / "cusp_skill.csv").set_index("predictor")
    preds = [p for p in sk.index if not p.startswith("esa_pfr")]
    c = pd.read_csv(T6 / "cusp_compare.csv")
    c = c[c.gipl_class.isin([1, 2]) & c[preds].notna().all(axis=1) & c.esa_pfr.notna() & (c.pf_obs == 0)]
    bins = np.arange(-8, 6.01, 0.5)
    ax.axvspan(-8, 0, color="#e8f1fc", lw=0)
    ax.text(-0.3, 0.98, "← frozen", transform=ax.get_xaxis_transform(), fontsize=6.5, color=INK2, ha="right",
            va="top")
    h, l = [], []
    for col, p, name in [(BLUE, "gipl_implied_d1m", "GIPL"), (ESA_C, "esa_d1m", "ESA CCI")]:
        x = np.clip(c[p].values, -7.99, 5.99)
        ax.hist(x, bins=bins, weights=np.full(x.size, 100 / x.size), histtype="step", lw=1.3, color=col)
        h.append(plt.Line2D([], [], color=col, lw=1.3))
        l.append(f"{name}:\n{100 * (c[p] < 0).mean():.0f} % frozen")
    ax.legend(h, l, loc="upper left", bbox_to_anchor=(0, 0.9), frameon=False, fontsize=6.5, handlelength=1.0,
              handletextpad=0.4, labelspacing=0.6, borderaxespad=0.2)
    ax.axvline(0, color=INK2, lw=0.6)
    ax.set_xlim(-8, 6)
    ax.set_xticks([-8, -4, 0, 4])
    ax.set_ylim(0, 29)
    ax.set_xlabel("dataset temperature at 1 m (°C)")
    ax.set_ylabel("% of sites")
    ax.set_title(f"c. {len(c):,} sites with no permafrost", pad=3)
    clean(ax)
    fig.savefig(FIG / "gipl_trust_2_cold.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("boreholes 1 m", len(d), f"GIPL {e_gipl:+.2f} ESA {e_esa:+.2f}", "CUSP no-PF", len(c))


def ncar_air():
    """SNAP 2 km NCAR-CCSM4 MAAT (mean of 12 monthly tas), statewide median of normal permafrost cells (every 10th),
    2021-2035, read from SNAP's archive zips (read-only). Cached in <data>/results/t6/trust_ncar_air.csv."""
    out = T6 / "trust_ncar_air.csv"
    if out.exists():
        return pd.read_csv(out, index_col="year")
    import rasterio
    zips = Path("/import/SNAP/poseidon/CKAN/CKAN_Data/Base/AK_CAN_2km/projected/AR5_CMIP5_models/"
                "Projected_Monthly_and_Derived_Temperature_Products_2km_CMIP5_AR5/monthly")
    ok = np.flatnonzero((CELLS["cls"] == 2) & (CELLS["pfr_2023"] > 0))[::10]
    x, y = CELLS["x"][ok], CELLS["y"][ok]
    i = ((C.TAS_NY - 1) - np.floor((y - C.TAS_Y0) / C.TAS_RES)).astype(int)
    j = np.floor((x - C.TAS_X0) / C.TAS_RES).astype(int)
    rows = []
    for yr in range(2021, 2036):
        row = {"year": yr}
        for scen in ["rcp45", "rcp85"]:
            acc = np.zeros(ok.size)
            for mo in range(1, 13):
                with rasterio.open(f"/vsizip/{zips}/tas_mean_C_AK_CAN_AR5_CCSM4_{scen}_01_2006-12_2100.zip/tas/"
                                   f"tas_mean_C_AR5_CCSM4_{scen}_{mo:02d}_{yr}.tif") as r:
                    acc += r.read(1)[i, j] / 12
            row[scen] = float(np.median(acc))
        rows.append(row)
    df = pd.DataFrame(rows).set_index("year")
    df.to_csv(out)
    return df


def fig_startup():
    """Scenario colour as in fig_air (blue RCP 4.5, orange RCP 8.5). b: NCAR-CCSM4's 2023 spike against its own air
    temperature. c, d: the 5-model average is the thick pale line and GFDL-CM3 the thin dark line, so identical values
    show as the thin line inside the thick one."""
    s = pd.read_csv(T6 / "startup_series.csv")
    s = s[(s.region == "Statewide") & (s.year <= 2050)]
    air = ncar_air()
    fig = plt.figure(figsize=(W, 2.1))
    gs = fig.add_gridspec(1, 4, wspace=0.28, left=0.06, right=0.995, bottom=0.145, top=0.86)
    ax = fig.add_subplot(gs[0])
    ax.axvspan(2020.5, 2023.5, color=GRID, lw=0)
    ax.axvspan(2023.5, 2035.5, color=LAND_C, lw=0)
    ax.text(2022, 0.98, "start-up", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.5,
            color=INK2)
    ax.text(2029.5, 0.03, "in lockstep", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=6.5, color=INK2)
    for scen, col, lab in [("rcp45", BLUE, "RCP 4.5"), ("rcp85", ORANGE, "RCP 8.5")]:
        d = s[(s.run == "5ModelAvg") & (s.scen == scen) & (s.depth == "magt1m")]
        ax.plot(d.year, d.gipl_median, color=col, lw=1.4, label=lab)
    ax.set_title("a. 1 m, 5-model average", pad=3)
    ax.set_ylabel("median temperature (°C)")
    ax.legend(frameon=False, loc="lower right", fontsize=6.5, handlelength=1.2)
    ax.annotate("+1.8 °C in\ntwo years", xy=(2021.9, -2.8), xytext=(2024.2, -3.25), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    ax.set_xlim(2020.5, 2050.5)
    ax.set_xticks([2025, 2035, 2045])
    clean(ax)

    ax = fig.add_subplot(gs[1])
    ax.axvspan(2022.5, 2023.5, color=LAND_C, lw=0)
    o = s[(s.run == "5ModelAvg") & (s.scen == "rcp45") & (s.depth == "magtsurface") & (s.year <= 2030)]
    ax.plot(o.year, o.gipl_median, color=PF_C, lw=3.2, solid_capstyle="round", zorder=1)
    dash = (0, (2.5, 1.5))
    for scen, col in [("rcp45", BLUE), ("rcp85", ORANGE)]:
        d = s[(s.run == "NCAR-CCSM4") & (s.scen == scen) & (s.depth == "magtsurface") & (s.year <= 2030)]
        ax.plot(d.year, d.gipl_median, color=col, lw=1.4, zorder=3)
        a = air.loc[2021:2030, scen]
        ax.plot(a.index, a.values, color=col, lw=0.8, ls=dash, zorder=2)
    h = [plt.Line2D([], [], color=INK2, lw=1.4), plt.Line2D([], [], color=INK2, lw=0.8, ls=dash),
         plt.Line2D([], [], color=PF_C, lw=3.2)]
    ax.legend(h, ["ground surface", "air temperature", "other runs"], loc="upper right", frameon=False,
              fontsize=6.5, handlelength=1.6, borderaxespad=0.1)
    ax.text(2023.6, -6.4, "2023", fontsize=6.5, color=INK2, va="center")
    ax.set_title("b. Surface, NCAR-CCSM4", pad=3)
    ax.set_xlim(2020.5, 2030.5)
    ax.set_xticks([2022, 2026, 2030])
    clean(ax)

    pale = {"rcp45": "#9ec5f4", "rcp85": "#f4b393"}
    dark = {"rcp45": "#1c5cab", "rcp85": "#c2410c"}
    first = None
    for k, (scen, shift, band, glab) in enumerate([("rcp45", 0, "identical", "GFDL-CM3"),
                                                   ("rcp85", 1, "same sequence,\none year apart",
                                                    "GFDL-CM3,\n1 year later")]):
        ax = fig.add_subplot(gs[k + 2], sharey=first)
        first = first or ax
        ax.axvspan(2020.5, 2035.5, color=LAND_C, lw=0)
        ax.text(2028, 0.98, band, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.5,
                color=INK2)
        a = s[(s.run == "5ModelAvg") & (s.scen == scen) & (s.depth == "magtsurface")]
        g = s[(s.run == "GFDL-CM3") & (s.scen == scen) & (s.depth == "magtsurface")]
        ax.plot(a.year, a.gipl_median, color=pale[scen], lw=3.2, solid_capstyle="round", label="5-model avg.")
        keep = g.year + shift <= 2050
        ax.plot(g.year[keep] + shift, g.gipl_median[keep], color=dark[scen], lw=0.9, label=glab)
        ax.set_title(f"{'cd'[k]}. Surface, RCP {scen[3]}.{scen[4]}", pad=3)
        ax.legend(loc="upper left", bbox_to_anchor=(0, 0.83), frameon=False, fontsize=6.5, handlelength=1.0,
                  handletextpad=0.4, borderaxespad=0.1)
        ax.set_xlim(2020.5, 2050.5)
        ax.set_xticks([2025, 2035, 2045])
        clean(ax)
        if k:
            plt.setp(ax.get_yticklabels(), visible=False)
    fig.savefig(FIG / "gipl_trust_3_startup.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_air():
    z = CELLS
    ok = np.flatnonzero((z["cls"] == 2) & (z["pfr_2023"] > 0))[::4]
    yrs = np.arange(2026, 2101)
    out = {}
    for scen in ["rcp45", "rcp85"]:
        g = np.asarray(stack(f"gipl_5ModelAvg_{scen}_magtsurface")[5:80][:, ok], "float32")  # 2026-2100
        a = np.asarray(stack(f"maat_{scen}")[20:95][:, ok], "float32")  # 2026-2100
        out[("GIPL ground surface", scen)] = np.median(g - g[:10].mean(0), axis=1)
        out[("Air (SNAP projections)", scen)] = np.median(a - a[:10].mean(0), axis=1)
    fig, axs = plt.subplots(1, 2, figsize=(3.55, 2.15), sharey=True,
                            gridspec_kw=dict(wspace=0.12, left=0.14, right=0.84, bottom=0.13, top=0.86))
    for ax, src, ttl in zip(axs, ["Air (SNAP projections)", "GIPL ground surface"], ["a. Air", "b. GIPL surface"]):
        for scen, col, lab in [("rcp45", BLUE, "RCP 4.5"), ("rcp85", ORANGE, "RCP 8.5")]:
            v = out[(src, scen)]
            ax.plot(yrs, v, color=col, lw=1.0)
            if ax is axs[1]:
                ax.text(2102, v[-5:].mean(), lab, fontsize=6.5, color=INK2, va="center", clip_on=False)
        ax.axhline(0, color=INK2, lw=0.6)
        ax.set_title(ttl, pad=3)
        ax.set_xticks([2030, 2065, 2100])
        clean(ax)
    tr = pd.read_csv(T6 / "trends.csv")
    tr = tr[(tr.source == "GIPL vs model air") & (tr.period == "2036-2070") & (tr.depth == "magtsurface")
            & (tr.region == "Statewide")].set_index("scen")
    a45, a85, g45, g85 = (tr.loc[s, k] for k in ["air_trend", "ground_trend"] for s in ["rcp45", "rcp85"])  # °C/decade
    for ax, r45, r85 in [(axs[0], a45, a85), (axs[1], g45, g85)]:
        ax.text(2027, 5.9, f"2036–2070, per decade:\nRCP 4.5  +{r45:.1f} °C\nRCP 8.5  +{r85:.1f} °C", fontsize=6,
                color=INK, va="top")
    axs[0].set_ylabel("warming since 2026–2035 (°C)")
    fig.savefig(FIG / "gipl_trust_4_air.pdf", dpi=400, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    for k, v in out.items():
        print(k, "2081-2100", round(float(v[55:].mean()), 2), "2061-2070", round(float(v[35:45].mean()), 2))


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
        for f in [fig_stuck, fig_cold, fig_startup, fig_air]:
            f()
            print(f.__name__, flush=True)
