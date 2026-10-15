"""T1 (statewide): can MAAT stand in for MAGT 1 m? Tested only on cells where GIPL works.

Domain: GIPL valid, ESA PFR > 0 (2020), NOT frozen in any GIPL run and NOT within 2 km of a frozen cell
(class 2 of statewide_frozen_class.tif from t3c_gipl_statewide.py).
  - Projected: GIPL 5ModelAvg magt1m / magtsurface vs SNAP 2 km 5modelAvg MAAT, eras x RCP 4.5/8.5.
    Levels (spatial) and changes vs the 2026-2035 baseline (GIPL spin-up skipped).
  - Historical: ESA CCI T1m / GST vs CRU TS 4.08 MAAT, 2000-2020 (ESA is unaffected by the GIPL artefact, so this
    is also reported for the masked cells).
MAAT 2 km is sampled at each 1 km cell centre (parent cell). Index-relevant metrics: Spearman rho, R2 of a linear
fit, and the agreement of 0-1 scores (1st/99th percentile clip-normalization) incl. the share of cells whose quintile
class changes.
Outputs: <data>/results/t1_maat_vs_magt.csv, docs/figures/t1_maat_vs_magt_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from pyproj import Transformer
from scipy.stats import spearmanr

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

GIPL = C.DATA / "gipl_tif"
TAS = C.DATA / "tas_tif"
OUT = C.DATA / "results"
FIG = C.REPO / "docs/figures"
BASE = (2026, 2035)
ERAS = {"2021-2050": (2021, 2050), "2051-2080": (2051, 2080), "2081-2100": (2081, 2100)}
HIST = (2000, 2020)
INK, INK2 = "#0b0b0b", "#52514e"
RNG = np.random.default_rng(0)


def read(p):
    with rasterio.open(p) as s:
        a = s.read(1).astype("float32")
    a[(a < -1000) | (a > 1000)] = np.nan
    return a


def gipl_mean(var, scen, y0, y1):
    unit = "degC"
    return np.nanmean([read(GIPL / var / f"gipl_5ModelAvg_{scen}_{var}_{unit}_{y}.tif") for y in range(y0, y1 + 1)], 0)


def maat_mean(kind, y0, y1):
    """Mean annual air temperature on the 2 km grid: mean of all monthly files in [y0, y1]."""
    acc, n = 0.0, 0
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            if kind == "cru":
                p = TAS / "cru_ts408" / f"tas_mean_C_cru_ts408_historical_{m:02d}_{y}.tif"
            else:
                p = TAS / f"5modelAvg_{kind}" / f"tas_mean_C_AR5_5modelAvg_{kind}_{m:02d}_{y}.tif"
            acc, n = acc + read(p), n + 1
    return acc / n


def cell_centres(prof):
    t = prof["transform"]
    xs = t.c + (np.arange(prof["width"]) + 0.5) * t.a
    ys = t.f + (np.arange(prof["height"]) + 0.5) * t.e
    return np.meshgrid(xs, ys)


def to_gipl(a2k, X, Y):
    """Sample a 2 km tas array (parent cell) at GIPL cell centres."""
    j = np.floor((X - C.TAS_X0) / C.TAS_RES).astype(int)
    i = (C.TAS_NY - 1) - np.floor((Y - C.TAS_Y0) / C.TAS_RES).astype(int)  # tas rows run north -> south
    ok = (i >= 0) & (i < a2k.shape[0]) & (j >= 0) & (j < a2k.shape[1])
    out = np.full(X.shape, np.nan, "float32")
    out[ok] = a2k[i[ok], j[ok]]
    return out


def esa_mean(var, X, Y):
    lon, lat = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True).transform(X, Y)
    acc, n = 0.0, 0
    for y in range(HIST[0], HIST[1] + 1):
        f = next((C.ESA_AK / "permafrost_gt").glob(f"*-{y}-fv05.0.nc"))
        ds = xr.open_dataset(f)
        la, lo = ds.lat.values.astype(float), ds.lon.values.astype(float)
        i = np.rint((lat - la[0]) / (la[1] - la[0])).astype(int)
        j = np.rint((lon - lo[0]) / (lo[1] - lo[0])).astype(int)
        ok = (i >= 0) & (i < la.size) & (j >= 0) & (j < lo.size)
        a = ds[var].values[0]
        v = np.full(X.shape, np.nan, "float32")
        v[ok] = a[i[ok], j[ok]]
        acc, n = acc + v, n + 1
    return acc / n


def norm01(a):
    lo, hi = np.nanpercentile(a, [1, 99])
    return np.clip((a - lo) / (hi - lo), 0, 1)


def compare(x, y, label, m):
    """x = MAAT term, y = ground-temperature term, both on GIPL cells; m = domain mask."""
    ok = m & np.isfinite(x) & np.isfinite(y)
    xv, yv = x[ok], y[ok]
    rho = spearmanr(xv, yv).statistic
    r = np.corrcoef(xv, yv)[0, 1]
    slope, icpt = np.polyfit(xv, yv, 1)
    sx, sy = norm01(xv), norm01(yv)
    qx = np.digitize(sx, np.nanpercentile(sx, [20, 40, 60, 80]))
    qy = np.digitize(sy, np.nanpercentile(sy, [20, 40, 60, 80]))
    return dict(comparison=label, n=int(ok.sum()), spearman=rho, pearson=r, r2=r * r, slope=slope,
                intercept=icpt, score_mae=float(np.mean(np.abs(sx - sy))),
                quintile_changed=float(np.mean(qx != qy)), quintile_off_by_2plus=float(np.mean(np.abs(qx - qy) >= 2)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT / "gipl_artifact/statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    assert cls.max() == 4, "expects the 5-class frozen_class (0 nodata,1 noPF,2 PF,3 border,4 frozen)"
    good, masked, pf_all = cls == 2, cls >= 3, cls >= 2
    X, Y = cell_centres(prof)
    rows, keep = [], {}

    # --- historical, ESA vs CRU (independent of GIPL)
    maat_h = to_gipl(maat_mean("cru", *HIST), X, Y)
    for var in ["T1m", "GST"]:
        e = esa_mean(var, X, Y)
        keep[f"esa_{var}"] = e
        for name, m in [("good", good), ("masked (frozen + border)", masked), ("all PFR>0", pf_all)]:
            rows.append(dict(period="2000-2020", scenario="hist", source=f"ESA {var}", domain=name,
                             **compare(maat_h, e, f"CRU MAAT vs ESA {var}", m)))
    keep["maat_hist"] = maat_h
    print(pd.DataFrame(rows).round(3).to_string(index=False), flush=True)

    # --- projected, GIPL vs MAAT on the good cells
    for scen in ["rcp45", "rcp85"]:
        mb = to_gipl(maat_mean(scen, *BASE), X, Y)
        gb = {v: gipl_mean(v, scen, *BASE) for v in ["magt1m", "magtsurface"]}
        rows.append(dict(period="2026-2035", scenario=scen, source="GIPL magt1m", domain="good",
                         **compare(mb, gb["magt1m"], "MAAT vs GIPL magt1m", good)))
        for era, (y0, y1) in ERAS.items():
            me = to_gipl(maat_mean(scen, y0, y1), X, Y)
            for v in ["magt1m", "magtsurface"]:
                ge = gipl_mean(v, scen, y0, y1)
                rows.append(dict(period=era, scenario=scen, source=f"GIPL {v}", domain="good",
                                 **compare(me, ge, f"MAAT vs GIPL {v}", good)))
                if era != "2021-2050":
                    rows.append(dict(period=f"change {era} vs 2026-2035", scenario=scen, source=f"GIPL {v}",
                                     domain="good", **compare(me - mb, ge - gb[v], f"dMAAT vs dGIPL {v}", good)))
                if (scen, era, v) == ("rcp85", "2051-2080", "magt1m"):
                    keep["maat_e2"], keep["magt1m_e2"] = me, ge
                    keep["dmaat_e2"], keep["dmagt1m_e2"] = me - mb, ge - gb[v]
            print(scen, era, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "t1_maat_vs_magt.csv", index=False)
    with pd.option_context("display.width", 250):
        print(df.drop(columns=["intercept"]).round(3).to_string(index=False))
    np.savez_compressed(OUT / "t1_maat_vs_magt_grids.npz", cls=cls, **keep)
    plot(keep, good, masked, prof)


def plot(k, good, masked, prof):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    panels = [("CRU MAAT 2000–2020 (°C)", "ESA T1m 2000–2020 (°C)", k["maat_hist"], k["esa_T1m"], good | masked,
               "Historical, ESA (all PFR > 0 cells)"),
              ("MAAT 2051–2080, RCP 8.5 (°C)", "GIPL magt1m 2051–2080 (°C)", k["maat_e2"], k["magt1m_e2"], good,
               "Projected levels, GIPL (good cells)"),
              ("ΔMAAT (°C)", "ΔGIPL magt1m (°C)", k["dmaat_e2"], k["dmagt1m_e2"], good,
               "Projected change 2051–2080 vs 2026–2035, RCP 8.5")]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, (xl, yl, x, y, m, title) in zip(axs, panels):
        ok = m & np.isfinite(x) & np.isfinite(y)
        hb = ax.hexbin(x[ok], y[ok], gridsize=70, bins="log", cmap="Blues", mincnt=1)
        rho = spearmanr(x[ok], y[ok]).statistic
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_title(f"{title}\nSpearman ρ = {rho:.2f}, n = {ok.sum():,}", loc="left", fontsize=9.5, color=INK)
        fig.colorbar(hb, ax=ax, shrink=0.8, label="cells (log)")
    fig.tight_layout()
    fig.savefig(FIG / "t1_maat_vs_magt_scatter.png", dpi=150, bbox_inches="tight")

    # residual map: what MAAT does not explain (GIPL magt1m 2051-2080 RCP 8.5, good cells)
    x, y = k["maat_e2"], k["magt1m_e2"]
    ok = good & np.isfinite(x) & np.isfinite(y)
    b = np.polyfit(x[ok], y[ok], 1)
    res = np.full(x.shape, np.nan)
    res[ok] = y[ok] - np.polyval(b, x[ok])
    t = prof["transform"]
    ext = (t.c, t.c + prof["width"] * t.a, t.f + prof["height"] * t.e, t.f)
    from matplotlib.colors import LinearSegmentedColormap
    div = LinearSegmentedColormap.from_list("cw", ["#0d366b", "#3987e5", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                   "#7a1d1c"])
    div.set_bad((0, 0, 0, 0))
    bg = np.where(masked, 1.0, np.nan)
    fig, ax = plt.subplots(figsize=(12, 9.5))
    ax.imshow(bg, extent=ext, cmap=matplotlib.colors.ListedColormap(["#cfcdc6"]), vmin=0, vmax=2, interpolation="nearest")
    im = ax.imshow(res, extent=ext, cmap=div, vmin=-3, vmax=3, interpolation="nearest")
    fig.colorbar(im, ax=ax, shrink=0.6, label="GIPL magt1m − linear fit on MAAT (°C)")
    ax.set_title("What MAAT misses: GIPL 1 m MAGT residual, 2051–2080 RCP 8.5 (grey = masked GIPL artefact)",
                 loc="left", fontsize=11, color=INK)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    fig.savefig(FIG / "t1_maat_vs_magt_residual_map.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
