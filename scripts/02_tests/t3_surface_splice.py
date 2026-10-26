"""T3 / Q8: joining ESA CCI ground surface temperature (GST, observation-based, 2000-2023) to GIPL surface MAGT
(projections). Domain: ESA PFR > 0 (2023) & GIPL class 2 (D17); statewide and by region.

GIPL years are climate years (files labelled 20 years later, GIPL_ISSUE_3.md), so GIPL and ESA share the decade
2014-2023 (GIPL files 2034-2043; climate years 2014-2015 observed CRU, 2016-2023 projected) and can be compared
directly, without an expected-warming adjustment:
  offset = GIPL magtsurface 2014-2023 - ESA GST 2014-2023 (5ModelAvg, per RCP)
Join methods, judged by the cell-level jump between ESA 2014-2023 and the joined value for 2014-2023:
(a) none; (b) one statewide median offset; (c) regional median offsets;
(d) delta change method = ESA GST 2014-2023 + (GIPL era - GIPL 2014-2023): GIPL contributes only its change (D25).
Plus a test-area (pilot-window) time series (ESA annual 2000-2023, GIPL raw, delta change method joined).
Outputs: <data>/results/t3/splice_methods.csv; docs/figures/t3_splice_{map,scatter,pilots}.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import spearmanr

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = C.DATA / "results/t3"
FIG = C.REPO / "docs/figures"
SCENS = ["rcp45", "rcp85"]
REGIONS = {1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
REGION_C = {"Arctic": "#2a78d6", "Interior": "#eb6834", "West": "#1baf7a", "South": "#eda100"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                "#7a1d1c"])
DIV.set_bad("#ffffff")


def q(a):
    return dict(median=np.nanmedian(a), p10=np.nanpercentile(a, 10), p90=np.nanpercentile(a, 90),
                mad=np.nanmedian(np.abs(a - np.nanmedian(a))), abs_median=np.nanmedian(np.abs(a)),
                abs_p90=np.nanpercentile(np.abs(a), 90))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg, prof = s.read(1), s.profile
    dom = (f.pfr_pos.values == 1) & (f.gipl_class.values == 2)
    esa = f.esa_gst_recent.values
    rows, keep = [], {}
    for scen in SCENS:
        gb = f[f"gipl_sfc_{scen}_base"].values  # climate years 2014-2023, same decade as ESA
        off = gb - esa
        keep[scen] = off
        for rname, m in [("Statewide", dom)] + [(n, dom & (reg == k)) for k, n in REGIONS.items()]:
            ok = m & np.isfinite(off)
            rho = spearmanr(esa[ok][::7], gb[ok][::7]).statistic
            d_state = off[ok] - np.nanmedian(off[dom])
            d_reg = off[ok] - np.nanmedian(off[ok])
            for method, jump in [("a none", off[ok]), ("b statewide offset", d_state), ("c regional offset", d_reg),
                                 ("d change-only", np.zeros(ok.sum()))]:
                rows.append(dict(scen=scen, region=rname, n=int(ok.sum()), method=method, rho_esa_vs_gipl=rho,
                                 offset=np.nanmedian(off[ok]), share_gipl_colder=np.mean(off[ok] < 0),
                                 **{f"jump_{k}": v for k, v in q(jump).items()}))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "splice_methods.csv", index=False)
    with pd.option_context("display.width", 250):
        a = df[df.method == "a none"][["scen", "region", "n", "rho_esa_vs_gipl", "offset", "share_gipl_colder",
                                       "jump_p10", "jump_p90"]]
        print("Offsets, GIPL - ESA, both 2014-2023:")
        print(a.round(2).to_string(index=False))
        print("\nCell-level jump at the join (|jump| median / p90), by method:")
        print(df.pivot_table(index=["scen", "region"], columns="method", values="jump_abs_p90", sort=False)
              .round(2).to_string())
    plot_map_dist(keep, dom, reg, esa, f)
    plot_pilots()


def plot_map_dist(keep, dom, reg, esa, f):
    off = keep["rcp85"]
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    g = np.where(dom, off, np.nan)
    im = axs[0].imshow(g, cmap=DIV, vmin=-3, vmax=3, interpolation="nearest")
    fig.colorbar(im, ax=axs[0], shrink=0.75, label="GIPL − ESA (°C)")
    axs[0].set_title("Offset: GIPL surface vs ESA GST, both 2014–2023 (RCP 8.5)", loc="left", fontsize=10)
    axs[0].set_xticks([]); axs[0].set_yticks([])
    ax = axs[1]
    bins = np.linspace(-5, 5, 101)
    for k, rname in REGIONS.items():
        v = off[dom & (reg == k) & np.isfinite(off)]
        ax.hist(np.clip(v, -5, 5), bins=bins, weights=np.full(v.size, 100 / v.size), histtype="step", lw=1.8,
                color=REGION_C[rname], label=f"{rname}: median {np.median(v):+.2f} °C")
    ax.axvline(0, color=INK2, lw=0.8, ls=(0, (2, 2)))
    ax.set_xlabel("GIPL − ESA (°C)"); ax.set_ylabel("% of region's cells")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("By region (RCP 8.5)", loc="left", fontsize=10)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "t3_splice_map.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5.2))
    ok = dom & np.isfinite(esa)
    gb = f.gipl_sfc_rcp85_base.values
    hb = ax.hexbin(esa[ok], gb[ok], gridsize=80, bins="log", cmap="Blues", mincnt=1, extent=(-10, 6, -10, 6))
    ax.plot([-10, 6], [-10, 6], color=INK2, lw=0.8, ls=(0, (2, 2)))
    rho = spearmanr(esa[ok][::7], gb[ok][::7]).statistic
    ax.set_xlabel("ESA GST 2014–2023 (°C)"); ax.set_ylabel("GIPL surface MAGT 2014–2023, RCP 8.5 (°C)")
    ax.set_title(f"Same cells, same decade (Spearman ρ = {rho:.2f})", loc="left", fontsize=10)
    fig.colorbar(hb, ax=ax, shrink=0.8, label="cells (log)")
    fig.savefig(FIG / "t3_splice_scatter.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_pilots():
    """ESA annual GST (2000-2023) and GIPL surface (climate years 2004-2100, 5ModelAvg RCP 8.5): raw vs delta joined."""
    esa = xr.open_dataset(C.DATA / "esa/esa_pilot_cells.nc")
    cells = pd.read_csv(C.DATA / "windows/gipl_cells.csv")
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        rr, cc = rasterio.transform.rowcol(s.transform, cells.x.values, cells.y.values)
        good = s.read(1)[rr, cc] == 2
    years = np.arange(C.GIPL_START_OK, 2101)  # climate years after GIPL's start-up period
    g = np.full((len(cells), years.size), np.nan)
    for k, y in enumerate(years):
        fy = C.gipl_file_year(y, "5ModelAvg", "rcp85")
        with rasterio.open(C.DATA / f"gipl_tif/magtsurface/gipl_5ModelAvg_rcp85_magtsurface_degC_{fy}.tif") as s:
            g[:, k] = s.read(1)[rr, cc]
    g[g < -9000] = np.nan
    base = g[:, (years >= 2014) & (years <= 2023)].mean(1)
    e_rec = esa.GST.sel(year=slice(2014, 2023)).mean("year").values
    fig, axs = plt.subplots(1, 3, figsize=(15, 4), sharex=True)
    for ax, (key, label, *_rest) in zip(axs, C.REGIONS):
        m = (cells.region == key).values & good
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.plot(esa.year, np.nanmedian(esa.GST.values[m], 0), color=INK2, lw=2, label="ESA GST (observation-based)")
        ax.plot(years, np.nanmedian(g[m], 0), color="#2a78d6", lw=1.4, alpha=0.8, label="GIPL surface, raw")
        joined = e_rec[m, None] + (g[m] - base[m, None])
        joined[:, years < 2014] = np.nan
        ax.plot(years, np.nanmedian(joined, 0), color="#eb6834", lw=2, label="Delta change method (ESA + GIPL change)")
        ax.axvspan(2014, 2023, color="#e4e3df", alpha=0.6, lw=0)
        ax.set_title(f"{label} test area ({int(m.sum())} cells)", loc="left", fontsize=10)
        ax.set_ylabel("°C")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=9, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle("Surface temperature, median of test-area cells (5ModelAvg RCP 8.5, GIPL on climate years; "
                 "grey band = 2014–2023 reference)",
                 fontsize=10.5, y=1.08)
    fig.tight_layout()
    fig.savefig(FIG / "t3_splice_pilots.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
