"""Q12: does GIPL MAGT *surface* need the stuck-cell mask?

Groups (statewide_frozen_class.tif): stuck (4), border (3, within 2 km of stuck), and neighbours = good permafrost
cells (2) within NEIGH_KM of a stuck cell. For each run (3 models x 2 RCPs):
  - era means of magtsurface (2026-2035 baseline, 2021-2050, 2051-2080, 2081-2100) and change vs baseline;
  - group medians of level and change; year-to-year variability (std of annual differences);
  - annual group medians (time series).
For 5ModelAvg (local 5modelAvg MAAT): MAAT-controlled comparison = residuals of surface ~ MAAT (and dSurface ~ dMAAT)
from a linear fit on the neighbours.
Decision rule (Q12): if stuck ~ neighbours (|difference| <= 0.3 degC) in level and change -> surface can go unmasked.
Outputs: <data>/results/gipl_artifact/surface_mask_test.csv, surface_mask_series.csv;
docs/figures/t3h_surface_{series,residuals}.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage

from composite_indexing import config as C
from t1_maat_vs_magt import cell_centres, maat_mean, to_gipl

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TIF = C.DATA / "gipl_tif/magtsurface"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
MODELS, SCENS = ["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"], ["rcp45", "rcp85"]
YEARS = np.arange(2021, 2121)
PERIODS = {"2026-2035": (2026, 2035), "2021-2050": (2021, 2050), "2051-2080": (2051, 2080), "2081-2100": (2081, 2100)}
NEIGH_KM = 10
THRESH = 0.3
GROUP_C = {"stuck": "#c2410c", "border": "#eda100", "neighbours": "#2a78d6"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def read(p):
    with rasterio.open(p) as s:
        a = s.read(1).astype("float32")
    a[a < -9000] = np.nan
    return a


def main():
    with rasterio.open(OUT / "statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    stuck = cls == 4
    near = ndimage.distance_transform_edt(~stuck) <= NEIGH_KM
    groups = {"stuck": stuck, "border": cls == 3, "neighbours": (cls == 2) & near}
    print({g: int(m.sum()) for g, m in groups.items()}, flush=True)

    rows, series = [], []
    era = {}
    for model in MODELS:
        for scen in SCENS:
            sums = {p: 0.0 for p in PERIODS}
            prev, d1, d2, nd = None, 0.0, 0.0, 0
            for y in YEARS:
                a = read(TIF / f"gipl_{model}_{scen}_magtsurface_degC_{y}.tif")
                for g, m in groups.items():
                    series.append(dict(model=model, scen=scen, year=y, group=g, median=float(np.nanmedian(a[m]))))
                for p, (y0, y1) in PERIODS.items():
                    if y0 <= y <= y1:
                        sums[p] = sums[p] + a
                if prev is not None:
                    d = a - prev
                    d1, d2, nd = d1 + d, d2 + d * d, nd + 1
                prev = a
            iav = np.sqrt(np.maximum(d2 / nd - (d1 / nd) ** 2, 0))
            means = {p: sums[p] / (y1 - y0 + 1) for p, (y0, y1) in PERIODS.items()}
            if model == "5ModelAvg":
                era[scen] = means
            for p in PERIODS:
                lvl, chg = means[p], means[p] - means["2026-2035"]
                med = {g: (float(np.nanmedian(lvl[m])), float(np.nanmedian(chg[m])), float(np.nanmedian(iav[m])))
                       for g, m in groups.items()}
                rows.append(dict(model=model, scen=scen, period=p, kind="raw",
                                 **{f"{g}_level": v[0] for g, v in med.items()},
                                 **{f"{g}_change": v[1] for g, v in med.items()},
                                 **{f"{g}_iav": v[2] for g, v in med.items()}))
            print(model, scen, "done", flush=True)

    # MAAT-controlled (5ModelAvg)
    X, Y = cell_centres(prof)
    nb = groups["neighbours"]
    for scen in SCENS:
        maat = {p: to_gipl(maat_mean(scen, y0, y1), X, Y) for p, (y0, y1) in PERIODS.items()}
        for p in PERIODS:
            s_l, m_l = era[scen][p], maat[p]
            ok = nb & np.isfinite(s_l) & np.isfinite(m_l)
            b = np.polyfit(m_l[ok], s_l[ok], 1)
            res_l = s_l - np.polyval(b, m_l)
            s_c, m_c = s_l - era[scen]["2026-2035"], m_l - maat["2026-2035"]
            ok_c = nb & np.isfinite(s_c) & np.isfinite(m_c)
            bc = np.polyfit(m_c[ok_c], s_c[ok_c], 1) if p != "2026-2035" else np.array([0.0, 0.0])
            res_c = s_c - np.polyval(bc, m_c)
            rows.append(dict(model="5ModelAvg", scen=scen, period=p, kind="MAAT-controlled",
                             **{f"{g}_level": float(np.nanmedian(res_l[m])) for g, m in groups.items()},
                             **{f"{g}_change": float(np.nanmedian(res_c[m])) for g, m in groups.items()}))
            if (scen, p) == ("rcp85", "2081-2100"):
                keep = (res_l, res_c)
    df = pd.DataFrame(rows)
    for q in ["level", "change"]:
        df[f"stuck_minus_neighbours_{q}"] = df[f"stuck_{q}"] - df[f"neighbours_{q}"]
        df[f"border_minus_neighbours_{q}"] = df[f"border_{q}"] - df[f"neighbours_{q}"]
    df.to_csv(OUT / "surface_mask_test.csv", index=False)
    pd.DataFrame(series).to_csv(OUT / "surface_mask_series.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        cols = ["model", "scen", "period", "kind", "stuck_minus_neighbours_level", "stuck_minus_neighbours_change",
                "border_minus_neighbours_level", "border_minus_neighbours_change", "stuck_iav", "neighbours_iav"]
        print(df[cols].round(2).to_string(index=False))
    d = df[(df.period != "2026-2035") | (df.kind == "MAAT-controlled")]
    worst = d[["stuck_minus_neighbours_level", "stuck_minus_neighbours_change"]].abs().max()
    print("\nmax |stuck - neighbours| (level, change):", worst.round(2).to_dict(), "threshold", THRESH)
    plot(pd.DataFrame(series), keep, groups)


def plot(ser, keep, groups):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(2, 3, figsize=(14, 6.4), sharex=True, sharey=True)
    for j, model in enumerate(MODELS):
        for i, scen in enumerate(SCENS):
            ax = axs[i, j]
            ax.grid(axis="y", color=GRID, lw=0.6)
            for g, col in GROUP_C.items():
                s = ser[(ser.model == model) & (ser.scen == scen) & (ser.group == g)]
                ax.plot(s.year, s["median"], color=col, lw=1.8 if g != "border" else 1.2, label=g)
            ax.set_title(f"{model}, RCP {scen[3]}.{scen[4]}", loc="left", fontsize=10, color=INK)
            if j == 0:
                ax.set_ylabel("surface MAGT, group median (°C)")
    axs[0, 0].legend(frameon=False, fontsize=8.5)
    fig.suptitle(f"GIPL surface MAGT: stuck cells vs border cells vs good permafrost cells within {NEIGH_KM} km",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "t3h_surface_series.png", dpi=150, bbox_inches="tight")

    res_l, res_c = keep
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
    for ax, (r, lab) in zip(axs, [(res_l, "level, 2081–2100"), (res_c, "change, 2081–2100 vs 2026–2035")]):
        bins = np.linspace(-4, 4, 81)
        for g, col in GROUP_C.items():
            v = r[groups[g] & np.isfinite(r)]
            ax.hist(np.clip(v, -4, 4), bins=bins, weights=np.full(v.size, 100 / v.size), histtype="step", lw=1.8,
                    color=col, label=f"{g} (median {np.median(v):+.2f} °C)")
        ax.axvline(0, color=INK2, lw=0.8, ls=(0, (2, 2)))
        ax.set_xlabel(f"surface MAGT residual after MAAT (°C): {lab}")
        ax.set_title(f"5ModelAvg RCP 8.5: {lab}", loc="left", fontsize=10, color=INK)
        ax.legend(frameon=False, fontsize=8)
    axs[0].set_ylabel("% of cells in group")
    fig.tight_layout()
    fig.savefig(FIG / "t3h_surface_residuals.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
