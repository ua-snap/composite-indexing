"""T6 (GIPL_ISSUE_2): GIPL start-up period and level bias at the ground surface, 0.5 m, 1 m and 2 m. Can GIPL values be
used as absolute values (frozen / thawed around 0 degC), or only as a change signal?

Stage `prep` (slurm/17): annual stacks on every valid GIPL cell (statewide_frozen_class > 0, ~1.46 M cells), so all
later tests (start-up, drift, bias, 0 degC classes, site comparisons) read small arrays instead of 6000 GeoTIFFs.
  <data>/results/t6/cells.npz             cell index (flat index into the 1941 x 2471 grid), x, y, class, region, pfr_2023
  <data>/results/t6/gipl_<run>_<rcp>_<depth>.npy   float16 (100, ncell), FILE years 2021-2120 (= climate years
                                          2001-2100, GIPL_ISSUE_3.md), degC (NaN = nodata)
  <data>/results/t6/maat_<rcp>.npy        float16 (95, ncell), 2006-2100, SNAP 2 km 5modelAvg (parent cell)
  <data>/results/t6/maat_cru.npy          float16 (24, ncell), 2000-2023, CRU TS 4.08
  <data>/results/t6/esa_<var>.npy         float16 (24, ncell), 2000-2023, ESA CCI GST / T1m / T2m (nearest pixel), PFR
Runs: 5ModelAvg, GFDL-CM3, NCAR-CCSM4; RCP 4.5 / 8.5; depths: magtsurface, magt0.5m, magt1m, magt2m.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01_data"))

import numpy as np
import rasterio

from build_features import ESASampler
from composite_indexing import config as C
from t1_maat_vs_magt import cell_centres, read, to_gipl

OUT = C.DATA / "results/t6"
RUNS = ["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"]
SCENS = ["rcp45", "rcp85"]
DEPTHS = ["magtsurface", "magt0.5m", "magt1m", "magt2m"]
YEARS = np.arange(2021, 2121)
MAAT_YEARS = np.arange(2006, 2101)
OBS_YEARS = np.arange(2000, 2024)
ESA_VARS = [("permafrost_gt", "GST"), ("permafrost_gt", "T1m"), ("permafrost_gt", "T2m"), ("permafrost_pfr", "PFR")]


def annual_maat(kind, y):
    acc = 0.0
    for m in range(1, 13):
        if kind == "cru":
            p = C.DATA / "tas_tif/cru_ts408" / f"tas_mean_C_cru_ts408_historical_{m:02d}_{y}.tif"
        else:
            p = C.DATA / f"tas_tif/5modelAvg_{kind}" / f"tas_mean_C_AR5_5modelAvg_{kind}_{m:02d}_{y}.tif"
        acc = acc + read(p)
    return acc / 12


def prep():
    OUT.mkdir(parents=True, exist_ok=True)
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg = s.read(1)
    X, Y = cell_centres(prof)
    idx = np.flatnonzero(cls.ravel() > 0)
    esa = ESASampler(X, Y)
    pfr = esa.sample("permafrost_pfr", "PFR", 2023).ravel()[idx]
    np.savez(OUT / "cells.npz", idx=idx, x=X.ravel()[idx], y=Y.ravel()[idx], cls=cls.ravel()[idx],
             region=reg.ravel()[idx], pfr_2023=pfr, shape=np.array(cls.shape))
    print(f"{idx.size} valid GIPL cells", flush=True)
    t0 = time.time()

    for run in RUNS:
        for scen in SCENS:
            for dep in DEPTHS:
                path = OUT / f"gipl_{run}_{scen}_{dep}.npy"
                if path.exists():
                    continue
                st = np.full((YEARS.size, idx.size), np.nan, "float16")
                for k, y in enumerate(YEARS):
                    st[k] = read(C.DATA / f"gipl_tif/{dep}/gipl_{run}_{scen}_{dep}_degC_{y}.tif").ravel()[idx]
                np.save(path, st)
                print(f"{run} {scen} {dep} ({time.time() - t0:.0f} s)", flush=True)

    for scen in SCENS:
        path = OUT / f"maat_{scen}.npy"
        if not path.exists():
            st = np.stack([to_gipl(annual_maat(scen, y), X, Y).ravel()[idx] for y in MAAT_YEARS]).astype("float16")
            np.save(path, st)
            print(f"MAAT {scen} ({time.time() - t0:.0f} s)", flush=True)
    path = OUT / "maat_cru.npy"
    if not path.exists():
        np.save(path, np.stack([to_gipl(annual_maat("cru", y), X, Y).ravel()[idx] for y in OBS_YEARS])
                .astype("float16"))
        print(f"CRU ({time.time() - t0:.0f} s)", flush=True)
    for sub, var in ESA_VARS:
        path = OUT / f"esa_{var}.npy"
        if not path.exists():
            np.save(path, np.stack([esa.sample(sub, var, y).ravel()[idx] for y in OBS_YEARS]).astype("float16"))
            print(f"ESA {var} ({time.time() - t0:.0f} s)", flush=True)




# ---------------------------------------------------------------------------------------------------------------------
# Analysis stages (all read the stacks). Domain = ESA PFR 2023 > 0 & GIPL class 2 (stuck cells and their 2 km border
# excluded, D17), as in T3. GIPL is read on CLIMATE years: the stack row for climate year y is the file labelled
# C.gipl_file_year(y, run, scen) (20 years later; GIPL_ISSUE_3.md). `analyze` runs them all. Outputs in <data>/results/t6/:
#   startup:  startup_series.csv  annual medians per run / RCP / depth / region, by climate year 2001-2100
#                                 (5ModelAvg also GIPL - air: CRU to 2015, model air from 2016)
#             startup_gap.csv     median |RCP 8.5 - RCP 4.5| per climate year and depth, GIPL 5ModelAvg vs air
#   bias:     bias.csv            GIPL - ESA for the same years: 2014-2023 (the delta-method reference decade) and
#                                 2004-2015 (observed weather in both), per depth, run, RCP, region
#             bias_by_level.csv   median offset (2014-2023) in 1 degC bins of ESA level
#   drift:    drift.csv           extra GIPL warming under RCP 8.5 vs RCP 4.5 per degC of extra air warming
#   classes:  classes_mid.csv     team scheme (<= -1 / -1..0 / > 0 degC) at 2051-2080: raw GIPL vs ESA-adjusted
#                                 (ESA 2014-2023 + GIPL change from 2014-2023); grids.npz per-cell fields for maps
#   trends:   trends.csv          warming rates: ESA vs CRU 2003-2023, GIPL vs ESA 2004-2023, GIPL vs model air 2036-2070
REGIONS = {0: "Statewide", 1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
DEP_ESA = {"magtsurface": "GST", "magt1m": "T1m", "magt2m": "T2m"}
REF = (2014, 2023)  # delta-method reference decade = ESA's last decade
OBS = (2004, 2015)  # GIPL driven by observed (CRU) weather, after its start-up period (2001-2003)
MID = (2051, 2080)
LATE = (2081, 2100)
CLIM_YEARS = np.arange(2001, 2101)
EDGES = (-1.0, 0.0)  # team scheme: <= -1 good, -1..0 moderate, > 0 bad


def stack(name):
    return np.load(OUT / f"{name}.npy", mmap_mode="r")


def pmean(st, first_year, y0, y1, cols=None):
    a = st[y0 - first_year: y1 - first_year + 1]
    a = a[:, cols] if cols is not None else a
    return np.nanmean(np.asarray(a, "float32"), 0)


def gipl_rows(run, scen, years):
    return np.array([C.gipl_file_year(y, run, scen) - YEARS[0] for y in years])


def gipl(run, scen, dep, y0, y1, cols=None):
    """Mean over CLIMATE years y0-y1."""
    r = gipl_rows(run, scen, [y0, y1])
    return pmean(stack(f"gipl_{run}_{scen}_{dep}"), 0, r[0], r[1], cols)


def gipl_series(run, scen, dep, cols, years=CLIM_YEARS):
    """(climate year, cell) array; NaN where the run has no file for that year (GFDL-CM3 RCP 8.5 before 2002)."""
    r = gipl_rows(run, scen, years)
    ok = (r >= 0) & (r < YEARS.size)
    out = np.full((len(years), len(cols)), np.nan, "float32")
    out[ok] = np.asarray(stack(f"gipl_{run}_{scen}_{dep}")[r[ok]][:, cols], "float32")
    return out


def air_series(scen, cols, years=CLIM_YEARS):
    """Air temperature by climate year: CRU TS 4.08 to 2015 (GIPL's observed stretch), model air from 2016."""
    cru, mod = stack("maat_cru"), stack(f"maat_{scen}")
    out = np.full((len(years), len(cols)), np.nan, "float32")
    for k, y in enumerate(years):
        if OBS_YEARS[0] <= y <= 2015:
            out[k] = cru[y - OBS_YEARS[0]][cols]
        elif y >= 2016:
            out[k] = mod[y - MAAT_YEARS[0]][cols]
    return out


def maat(scen, y0, y1, cols=None):
    return pmean(stack(f"maat_{scen}"), MAAT_YEARS[0], y0, y1, cols)


def esa(var, y0, y1, cols=None):
    return pmean(stack(f"esa_{var}"), OBS_YEARS[0], y0, y1, cols)


def classify(t):
    c = np.digitize(t, EDGES, right=True).astype("float32")  # <= -1 -> 0, (-1, 0] -> 1, > 0 -> 2
    c[~np.isfinite(t)] = np.nan
    return c


def qstats(a):
    a = a[np.isfinite(a)]
    if a.size == 0:
        return dict(n=0)
    return dict(n=a.size, median=np.median(a), p10=np.percentile(a, 10), p25=np.percentile(a, 25),
                p75=np.percentile(a, 75), p90=np.percentile(a, 90), mean=a.mean())


def slope(a, years):
    """OLS slope per column (degC / yr), NaN-aware (needs >= 2/3 of the years)."""
    ok = np.isfinite(a)
    x = np.where(ok, years[:, None].astype("float32"), np.nan)
    xm, ym = np.nanmean(x, 0), np.nanmean(a, 0)
    s = np.nansum((x - xm) * (a - ym), 0) / np.nansum((x - xm) ** 2, 0)
    s[ok.sum(0) < 2 * len(years) // 3] = np.nan
    return s


def domain():
    z = np.load(OUT / "cells.npz")
    cols = np.flatnonzero((z["cls"] == 2) & (z["pfr_2023"] > 0))
    reg = z["region"][cols]
    return cols, {k: (np.ones(cols.size, bool) if k == 0 else reg == k) for k in REGIONS}


def startup():
    import pandas as pd
    cols, rmask = domain()
    rows = []
    for scen in SCENS:
        ma = air_series(scen, cols)
        for run in RUNS:
            for dep in DEPTHS:
                st = gipl_series(run, scen, dep, cols)
                for k, rn in REGIONS.items():
                    g = np.nanmedian(st[:, rmask[k]], 1)
                    d = (np.nanmedian(st[:, rmask[k]] - ma[:, rmask[k]], 1) if run == "5ModelAvg"
                         else np.full(CLIM_YEARS.size, np.nan))
                    rows += [dict(scen=scen, run=run, depth=dep, region=rn, year=int(yy), gipl_median=gv,
                                  gipl_minus_air_median=dv) for yy, gv, dv in zip(CLIM_YEARS, g, d)]
                print(f"series {scen} {run} {dep}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "startup_series.csv", index=False)

    rows = []
    m45, m85 = (air_series(s, cols) for s in SCENS)
    air_gap = np.nanmedian(np.abs(m85 - m45), 1)  # 0 to 2015: both scenarios carry the same observed weather
    for dep in DEPTHS:
        g45, g85 = (gipl_series("5ModelAvg", s, dep, cols) for s in SCENS)
        gap = np.nanmedian(np.abs(g85 - g45), 1)
        rows += [dict(depth=dep, year=int(y), gipl_gap=a, air_gap=b) for y, a, b in zip(CLIM_YEARS, gap, air_gap)]
    pd.DataFrame(rows).to_csv(OUT / "startup_gap.csv", index=False)
    print("startup done", flush=True)


def bias():
    from scipy.stats import spearmanr
    import pandas as pd
    cols, rmask = domain()
    rows, lvl, grids = [], [], {}
    for y0, y1 in (REF, OBS):
        e_ = {v: esa(v, y0, y1, cols) for v in DEP_ESA.values()}
        for scen in SCENS:
            for run in RUNS:
                for dep, ev in DEP_ESA.items():
                    g = gipl(run, scen, dep, y0, y1, cols)
                    off = g - e_[ev]
                    if run == "5ModelAvg":
                        grids[f"offset_{scen}_{dep}_{y0}"] = off
                    for k, rn in REGIONS.items():
                        m = rmask[k] & np.isfinite(off)
                        rows.append(dict(years=f"{y0}-{y1}", scen=scen, run=run, depth=dep, esa_var=ev, region=rn,
                                         rho=spearmanr(e_[ev][m][::5], g[m][::5]).statistic,
                                         share_colder=np.mean(off[m] < 0),
                                         **{f"offset_{kk}": vv for kk, vv in qstats(off[m]).items()}))
                    if run == "5ModelAvg" and (y0, y1) == REF:
                        b = np.floor(e_[ev])
                        for lo in range(-10, 5):
                            m = (b == lo) & np.isfinite(off)
                            if m.sum() >= 200:
                                lvl.append(dict(scen=scen, depth=dep, esa_bin=lo + 0.5, n=int(m.sum()),
                                                offset_median=np.median(off[m]), p25=np.percentile(off[m], 25),
                                                p75=np.percentile(off[m], 75)))
            print(f"bias {scen} {y0}-{y1}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "bias.csv", index=False)
    pd.DataFrame(lvl).to_csv(OUT / "bias_by_level.csv", index=False)
    np.savez_compressed(OUT / "grids_bias.npz", cols=cols, **{k: v.astype("float32") for k, v in grids.items()})


def drift():
    """How much more GIPL warms under RCP 8.5 than RCP 4.5 by 2081-2100 (from 2014-2023), per degC of extra air
    warming. 1 = GIPL passes on all extra air warming."""
    import pandas as pd
    cols, rmask = domain()
    rows = []
    dm = {s: maat(s, *LATE, cols) - maat(s, *REF, cols) for s in SCENS}
    for dep in DEPTHS:
        dg = {s: gipl("5ModelAvg", s, dep, *LATE, cols) - gipl("5ModelAvg", s, dep, *REF, cols) for s in SCENS}
        ex_air, ex_g = dm["rcp85"] - dm["rcp45"], dg["rcp85"] - dg["rcp45"]
        for k, rn in REGIONS.items():
            m = rmask[k] & np.isfinite(ex_g) & np.isfinite(ex_air)
            rows.append(dict(base=f"{REF[0]}-{REF[1]}", depth=dep, region=rn,
                             gipl_change_rcp45=np.median(dg["rcp45"][m]), gipl_change_rcp85=np.median(dg["rcp85"][m]),
                             air_change_rcp45=np.median(dm["rcp45"][m]), air_change_rcp85=np.median(dm["rcp85"][m]),
                             extra_air=np.median(ex_air[m]), extra_gipl=np.median(ex_g[m]),
                             ratio_of_medians=np.median(ex_g[m]) / np.median(ex_air[m])))
    pd.DataFrame(rows).to_csv(OUT / "drift.csv", index=False)
    print("drift done", flush=True)


def classes():
    import pandas as pd
    cols, rmask = domain()
    rows, grids = [], {}
    esa_ref = {v: esa(v, *REF, cols) for v in DEP_ESA.values()}
    for scen in SCENS:
        for dep in DEPTHS:
            gm = gipl("5ModelAvg", scen, dep, *MID, cols)
            c_raw = classify(gm)
            grids[f"mid_raw_{scen}_{dep}"] = gm
            c_adj = np.full(cols.size, np.nan, "float32")
            if dep in DEP_ESA:
                adj = esa_ref[DEP_ESA[dep]] + (gm - gipl("5ModelAvg", scen, dep, *REF, cols))
                c_adj = classify(adj)
                grids[f"mid_adj_{scen}_{dep}"] = adj
            for k, rn in REGIONS.items():
                m = rmask[k] & np.isfinite(c_raw)
                row = dict(scen=scen, depth=dep, region=rn, n=int(m.sum()))
                for i in range(3):
                    row[f"raw_{i}"] = np.mean(c_raw[m] == i)
                    row[f"adj_{i}"] = np.mean(c_adj[m] == i) if dep in DEP_ESA else np.nan
                if dep in DEP_ESA:
                    mm = m & np.isfinite(c_adj)
                    row["same_class"] = np.mean(c_raw[mm] == c_adj[mm])
                    row["raw_colder_class"] = np.mean(c_raw[mm] < c_adj[mm])
                    row["raw_warmer_class"] = np.mean(c_raw[mm] > c_adj[mm])
                    for i in range(3):
                        for j in range(3):
                            row[f"cm_{i}{j}"] = np.mean((c_raw[mm] == i) & (c_adj[mm] == j))
                row["raw_within_0p5_of_edge"] = np.mean(np.min(np.abs(gm[m, None] - np.array(EDGES)), 1) <= 0.5)
                row["raw_between_m1p5_and_0p5"] = np.mean((gm[m] > -1.5) & (gm[m] <= 0.5))
                rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "classes_mid.csv", index=False)
    np.savez_compressed(OUT / "grids.npz", cols=cols, **{k: v.astype("float32") for k, v in grids.items()})
    print("classes done", flush=True)


def trends():
    import pandas as pd
    cols, rmask = domain()
    rows = []
    obs = slice(2003 - OBS_YEARS[0], None)  # 2003+: one ESA product (MODIS LST + CryoGrid); 2000-2002 differ
    cru = slope(np.asarray(stack("maat_cru")[obs][:, cols], "float32"), OBS_YEARS[obs])
    for ev in DEP_ESA.values():
        s = slope(np.asarray(stack(f"esa_{ev}")[obs][:, cols], "float32"), OBS_YEARS[obs])
        for k, rn in REGIONS.items():
            m = rmask[k] & np.isfinite(s) & np.isfinite(cru)
            rows.append(dict(source="ESA vs CRU", period="2003-2023", scen="obs", depth=ev, region=rn,
                             ground_trend=np.median(s[m]) * 10, air_trend=np.median(cru[m]) * 10))
    yrs = np.arange(2004, 2024)  # same years in both: GIPL 2004-2015 observed weather, 2016-2023 projected
    for scen in SCENS:
        for dep, ev in DEP_ESA.items():
            g = slope(gipl_series("5ModelAvg", scen, dep, cols, yrs), yrs)
            e = slope(np.asarray(stack(f"esa_{ev}")[yrs[0] - OBS_YEARS[0]:][:, cols], "float32"), yrs)
            for k, rn in REGIONS.items():
                m = rmask[k] & np.isfinite(g) & np.isfinite(e)
                rows.append(dict(source="GIPL vs ESA", period="2004-2023", scen=scen, depth=dep, region=rn,
                                 ground_trend=np.median(g[m]) * 10, air_trend=np.nan, esa_trend=np.median(e[m]) * 10))
    for scen in SCENS:
        for y0, y1 in [(2036, 2070), (2016, 2050)]:
            yrs = np.arange(y0, y1 + 1)
            ma = slope(np.asarray(stack(f"maat_{scen}")[y0 - MAAT_YEARS[0]:y1 + 1 - MAAT_YEARS[0]][:, cols],
                                  "float32"), yrs)
            for dep in DEPTHS:
                s = slope(gipl_series("5ModelAvg", scen, dep, cols, yrs), yrs)
                for k, rn in REGIONS.items():
                    m = rmask[k] & np.isfinite(s) & np.isfinite(ma)
                    rows.append(dict(source="GIPL vs model air", period=f"{y0}-{y1}", scen=scen, depth=dep,
                                     region=rn, ground_trend=np.median(s[m]) * 10, air_trend=np.median(ma[m]) * 10))
    t = pd.DataFrame(rows)
    t["ratio"] = t.ground_trend / t.air_trend
    t.to_csv(OUT / "trends.csv", index=False)
    print("trends done", flush=True)


STAGES = {"prep": prep, "startup": startup, "bias": bias, "drift": drift, "classes": classes, "trends": trends}

if __name__ == "__main__":
    for st_ in (["startup", "bias", "drift", "classes", "trends"] if sys.argv[1] == "analyze" else sys.argv[1:]):
        STAGES[st_]()
