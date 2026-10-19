"""T3 (first look): can ESA CCI (2000-2023) and GIPL 5ModelAvg (2021-2120) be joined into one ground-temperature
record? Compared at two depth pairs: ESA GST <-> GIPL magtsurface, ESA T1m <-> GIPL magt1m, on the pilot 1 km cells.

Also characterizes the GIPL "stuck" magt1m cells (100-yr range < 0.1 degC) and what ESA shows there.
Outputs: docs/figures/t3_continuity.png, docs/figures/t3_stuck_cells.png, <data>/results/t3_*.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import spearmanr

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIG = C.REPO / "docs/figures"
RES = C.DATA / "results"
PAIRS = [("GST", "magtsurface_degC", "Ground surface"), ("T1m", "magt1m_degC", "1 m depth")]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
ESA_C, RCP_C = "#52514e", {"RCP 4.5": "#2a78d6", "RCP 8.5": "#eb6834"}
STUCK = 0.1  # degC: max - min of magt1m over 100 yr, 5ModelAvg, both scenarios


def load_gipl(cells):
    """GIPL 5ModelAvg on the pilot cells: dict field -> array (cell, scenario, year), plus years."""
    out, years = {}, None
    for region in cells.region.unique():
        ds = xr.open_dataset(next((C.DATA / "rasdaman_cache").glob(f"crrel_gipl_outputs_nc_wcs_pilot_{region}_*.nc")))
        ds = ds.isel(model=0)
        years = (pd.Timestamp("1601-01-01") + pd.to_timedelta(ds.time.values, "D")).year.values
        sub = cells[cells.region == region]
        for _, f, _ in PAIRS:
            a = ds[f].sel(X=xr.DataArray(sub.x.values), Y=xr.DataArray(sub.y.values), method="nearest")
            a = a.transpose("dim_0", "scenario", "time").values
            out.setdefault(f, np.full((len(cells), 2, len(years)), np.nan))[sub.index.values] = a
    return out, years


def trend(y, t):
    """OLS slope per row (degC/decade), NaN-safe."""
    t = t - t.mean()
    m = np.isfinite(y)
    yc = np.where(m, y - np.nanmean(y, 1, keepdims=True), 0)
    return 10 * (yc * t).sum(1) / (m * t ** 2).sum(1)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    cells = pd.read_csv(C.DATA / "windows/gipl_cells.csv")
    esa = xr.open_dataset(C.DATA / "esa/esa_pilot_cells.nc")
    ey = esa.year.values
    gipl, gy = load_gipl(cells)
    g1 = gipl["magt1m_degC"]
    stuck = (np.nanmax(g1, axis=(1, 2)) - np.nanmin(g1, axis=(1, 2))) < STUCK
    cells["stuck"] = stuck

    # --- overlap statistics per window and depth
    rows = []
    for region in cells.region.unique():
        m = (cells.region == region).values
        for ev, gv, label in PAIRS:
            e = esa[ev].values[m]
            g = gipl[gv][m].mean(1)  # scenarios are near-identical early on
            e_ov = e[:, np.isin(ey, [2021, 2022, 2023])].mean(1)
            g_ov = g[:, np.isin(gy, [2021, 2022, 2023])].mean(1)
            ok = np.isfinite(e_ov) & np.isfinite(g_ov)
            rows.append(dict(
                region=region, depth=label, n=int(ok.sum()),
                esa_2021_23=np.median(e_ov[ok]), gipl_2021_23=np.median(g_ov[ok]),
                bias_median=np.median(g_ov[ok] - e_ov[ok]), mae=np.mean(np.abs(g_ov[ok] - e_ov[ok])),
                spearman_r=spearmanr(e_ov[ok], g_ov[ok]).statistic,
                esa_trend_2000_23=np.nanmedian(trend(e, ey.astype(float))),
                gipl_trend_2021_50_rcp45=np.nanmedian(trend(gipl[gv][m][:, 0, (gy <= 2050)], gy[gy <= 2050].astype(float))),
                gipl_trend_2021_50_rcp85=np.nanmedian(trend(gipl[gv][m][:, 1, (gy <= 2050)], gy[gy <= 2050].astype(float))),
            ))
    stats = pd.DataFrame(rows)
    stats.to_csv(RES / "t3_overlap_stats.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(stats.round(2).to_string(index=False))

    # --- stuck cells: GIPL vs ESA
    fb = (cells.region == "fairbanks").values
    srow = []
    for name, m in [("stuck", fb & stuck), ("not stuck", fb & ~stuck)]:
        d = dict(group=name, n=int(m.sum()), esa_pfr_2020=np.nanmedian(esa.PFR.sel(year=2020).values[m]),
                 esa_alt=np.nanmedian(esa.ALT.values[m]))
        for ev, gv, label in PAIRS:
            d[f"esa_{ev}"] = np.nanmedian(esa[ev].values[m])
            d[f"esa_{ev}_trend"] = np.nanmedian(trend(esa[ev].values[m], ey.astype(float)))
            d[f"gipl_{gv}_2021_30"] = np.nanmedian(gipl[gv][m][:, :, gy <= 2030])
            d[f"gipl_{gv}_2091_2100_85"] = np.nanmedian(gipl[gv][m][:, 1, (gy >= 2091) & (gy <= 2100)])
        srow.append(d)
    sdf = pd.DataFrame(srow)
    sdf.to_csv(RES / "t3_stuck_cells.csv", index=False)
    print("\nFairbanks cells, GIPL magt1m stuck vs not:")
    print(sdf.round(2).T.to_string(header=False))
    pd.DataFrame(dict(cell=cells.index, region=cells.region, stuck=stuck)).to_csv(RES / "t3_stuck_flag.csv", index=False)

    # --- figure 1: continuity, windows x depth
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
    labels = {r[0]: r[1] for r in C.REGIONS}
    gm = gy <= 2100
    fig, axs = plt.subplots(3, 2, figsize=(10, 8.4), sharex=True)
    for i, region in enumerate(["brooks", "fairbanks", "denali"]):
        m = (cells.region == region).values
        for j, (ev, gv, label) in enumerate(PAIRS):
            ax = axs[i, j]
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.axhline(0, color=INK2, lw=0.8, ls=(0, (2, 2)))
            for k, (sc, col) in enumerate(RCP_C.items()):
                a = gipl[gv][m][:, k][:, gm]
                ax.fill_between(gy[gm], *np.nanpercentile(a, [10, 90], 0), color=col, alpha=0.15, lw=0)
                ax.plot(gy[gm], np.nanmedian(a, 0), color=col, lw=2)
            e = esa[ev].values[m]
            ax.fill_between(ey, *np.nanpercentile(e, [10, 90], 0), color=ESA_C, alpha=0.2, lw=0)
            ax.plot(ey, np.nanmedian(e, 0), color=ESA_C, lw=2)
            if i == 0:
                ax.set_title(f"{label}: ESA {ev} → GIPL {gv.replace('_degC', '')}", color=INK, fontsize=10, loc="left")
            if j == 0:
                ax.set_ylabel(f"{labels[region]}\n°C")
            if i == 0 and j == 1:  # direct labels once
                ax.text(2001, np.nanmedian(e[:, 0]) + 0.6, "ESA CCI", color=INK, fontsize=8)
                for k, (sc, col) in enumerate(RCP_C.items()):
                    ax.text(2101, np.nanmedian(gipl[gv][m][:, k][:, gm][:, -1]), f" {sc}", color=INK, fontsize=8,
                            va="center")
    for ax in axs[-1]:
        ax.set_xlim(1999, 2112)
    handles = [plt.Line2D([], [], color=ESA_C, lw=2, label="ESA CCI v5 (2000–2023)")] + [
        plt.Line2D([], [], color=c, lw=2, label=f"GIPL 5ModelAvg {s}") for s, c in RCP_C.items()]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, -0.01, "Lines: median of the 100 cells in each 10 × 10 km test area; bands: 10th–90th percentile.",
             ha="center", color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG / "t3_continuity.png", dpi=150, bbox_inches="tight")

    # --- figure 2: Fairbanks stuck vs not-stuck cells, 1 m and surface
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, (name, m) in zip(axs, [("GIPL 1 m stuck", fb & stuck), ("GIPL 1 m responsive", fb & ~stuck)]):
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.axhline(0, color=INK2, lw=0.8, ls=(0, (2, 2)))
        for ev, gv, ls in [("GST", "magtsurface_degC", (0, (4, 2))), ("T1m", "magt1m_degC", "-")]:
            ax.plot(gy[gm], np.nanmedian(gipl[gv][m][:, 1][:, gm], 0), color=RCP_C["RCP 8.5"], lw=2, ls=ls)
            ax.plot(ey, np.nanmedian(esa[ev].values[m], 0), color=ESA_C, lw=2, ls=ls)
        ax.set_title(f"Fairbanks, {name} (n = {int(m.sum())})", color=INK, fontsize=10, loc="left")
        ax.set_xlim(1999, 2101)
    axs[0].set_ylabel("°C")
    handles = [plt.Line2D([], [], color=ESA_C, lw=2, label="ESA CCI"),
               plt.Line2D([], [], color=RCP_C["RCP 8.5"], lw=2, label="GIPL 5ModelAvg RCP 8.5"),
               plt.Line2D([], [], color=INK2, lw=2, ls=(0, (4, 2)), label="surface"),
               plt.Line2D([], [], color=INK2, lw=2, label="1 m")]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "t3_stuck_cells.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
