"""T6 (GIPL_ISSUE_2): GIPL start-up period and level bias at the ground surface, 0.5 m, 1 m and 2 m. Can GIPL values be
used as absolute values (frozen / thawed around 0 degC), or only as a change signal?

Stage `prep` (slurm/17): annual stacks on every valid GIPL cell (statewide_frozen_class > 0, ~1.46 M cells), so all
later tests (start-up, drift, bias, 0 degC classes, site comparisons) read small arrays instead of 6000 GeoTIFFs.
  <data>/results/t6/cells.npz             cell index (flat index into the 1941 x 2471 grid), x, y, class, region, pfr_2023
  <data>/results/t6/gipl_<run>_<rcp>_<depth>.npy   float16 (100, ncell), 2021-2120, degC (NaN = nodata)
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
# excluded, D17), as in T3. `analyze` runs them all. Outputs in <data>/results/t6/:
#   startup:  startup_series.csv  annual medians per run / RCP / depth / region (GIPL; 5ModelAvg also GIPL - model air)
#             startup_gap.csv     median |RCP 8.5 - RCP 4.5| per year and depth, GIPL 5ModelAvg vs model air
#             shared_forcing.csv  per-cell correlation of year-to-year changes between runs / scenarios and with air
#   bias:     bias.csv            GIPL vs ESA 2014-2023 per depth (surface/GST, 1 m/T1m, 2 m/T2m), run, RCP, region,
#                                 for GIPL reference decades 2026-2035 and 2036-2045
#             bias_by_level.csv   median excess offset in 1 degC bins of ESA level
#   basestep: basestep.csv        GIPL change 2026-2035 -> 2036-2045 minus model air change (the 2036 switch)
#   drift:    drift.csv           extra GIPL warming under RCP 8.5 vs RCP 4.5 per degC of extra air warming
#   classes:  classes_mid.csv     team scheme (<= -1 / -1..0 / > 0 degC) at 2051-2080: raw GIPL vs ESA-adjusted
#             grids.npz           per-cell fields for maps
#   trends:   trends.csv          ground vs air warming rates: ESA vs CRU 2003-2023; GIPL vs model air 2036-2070
REGIONS = {0: "Statewide", 1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
DEP_ESA = {"magtsurface": "GST", "magt1m": "T1m", "magt2m": "T2m"}
BASE = (2026, 2035)
BASE2 = (2036, 2045)  # first decade after the 2021-2035 stretch shared by runs and scenarios (startup)
ESA_REF = (2014, 2023)
MID = (2051, 2080)
LATE = (2081, 2100)
EDGES = (-1.0, 0.0)  # team scheme: <= -1 good, -1..0 moderate, > 0 bad


def stack(name):
    return np.load(OUT / f"{name}.npy", mmap_mode="r")


def pmean(st, first_year, y0, y1, cols=None):
    a = st[y0 - first_year: y1 - first_year + 1]
    a = a[:, cols] if cols is not None else a
    return np.nanmean(np.asarray(a, "float32"), 0)


def gipl(run, scen, dep, y0, y1, cols=None):
    return pmean(stack(f"gipl_{run}_{scen}_{dep}"), YEARS[0], y0, y1, cols)


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


def change_corr(a, b, y0, y1, lag=0):
    """Per-cell correlation of year-to-year changes of two (year, cell) arrays starting in 2021; b shifted by lag."""
    i0, i1 = y0 - YEARS[0], y1 - YEARS[0]
    da = np.diff(a[i0:i1 + 1], axis=0)
    db = np.diff(b[i0 + lag:i1 + 1 + lag], axis=0)
    da, db = da - da.mean(0), db - db.mean(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (da * db).sum(0) / np.sqrt((da ** 2).sum(0) * (db ** 2).sum(0))


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
        ma = np.asarray(stack(f"maat_{scen}")[YEARS[0] - MAAT_YEARS[0]:][:, cols], "float32")  # 2021-2100
        for run in RUNS:
            for dep in DEPTHS:
                st = np.asarray(stack(f"gipl_{run}_{scen}_{dep}")[:, cols], "float32")
                for k, rn in REGIONS.items():
                    g = np.nanmedian(st[:, rmask[k]], 1)
                    d = np.full(YEARS.size, np.nan)
                    if run == "5ModelAvg":
                        d[:ma.shape[0]] = np.nanmedian(st[:ma.shape[0], rmask[k]] - ma[:, rmask[k]], 1)
                    rows += [dict(scen=scen, run=run, depth=dep, region=rn, year=int(yy), gipl_median=gv,
                                  gipl_minus_maat_median=dv) for yy, gv, dv in zip(YEARS, g, d)]
                print(f"series {scen} {run} {dep}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "startup_series.csv", index=False)

    rows = []
    m45, m85 = (np.asarray(stack(f"maat_{s}")[YEARS[0] - MAAT_YEARS[0]:][:, cols], "float32") for s in SCENS)
    air_gap = np.nanmedian(np.abs(m85 - m45), 1)
    for dep in DEPTHS:
        g45, g85 = (np.asarray(stack(f"gipl_5ModelAvg_{s}_{dep}")[:m45.shape[0]][:, cols], "float32") for s in SCENS)
        gap = np.nanmedian(np.abs(g85 - g45), 1)
        rows += [dict(depth=dep, year=int(y), gipl_gap=a, air_gap=b) for y, a, b in zip(YEARS, gap, air_gap)]
    pd.DataFrame(rows).to_csv(OUT / "startup_gap.csv", index=False)

    sub = cols[::10]
    rows = []
    for dep in ["magtsurface", "magt1m"]:
        g = {(r, s): np.asarray(stack(f"gipl_{r}_{s}_{dep}")[:, sub], "float32") for r in RUNS for s in SCENS}
        air = {s: np.asarray(stack(f"maat_{s}")[YEARS[0] - MAAT_YEARS[0]:][:, sub], "float32") for s in SCENS}
        pairs = [(("5ModelAvg", "rcp45"), ("5ModelAvg", "rcp85"), 0), (("5ModelAvg", "rcp45"), ("GFDL-CM3", "rcp45"), 0),
                 (("5ModelAvg", "rcp85"), ("GFDL-CM3", "rcp85"), 0), (("5ModelAvg", "rcp85"), ("GFDL-CM3", "rcp85"), -1),
                 (("NCAR-CCSM4", "rcp45"), ("NCAR-CCSM4", "rcp85"), 0), (("5ModelAvg", "rcp45"), ("NCAR-CCSM4", "rcp45"), 0)]
        for a, b, lag in pairs:
            for y0, y1 in [(2021, 2035), (2036, 2060), (2061, 2099)]:
                if lag < 0:  # b one year ahead of a: compare b(t) with a(t + 1)
                    r = change_corr(g[b], g[a], y0, min(y1, 2119) - 1, 1)
                else:
                    r = change_corr(g[a], g[b], y0, y1)
                rows.append(dict(depth=dep, a=" ".join(a), b=" ".join(b) + (" (1 yr ahead)" if lag else ""),
                                 period=f"{y0}-{y1}", median_r=np.nanmedian(r), share_r_above_0p9=np.nanmean(r > 0.9)))
        for r_ in RUNS:
            for s in SCENS:
                for y0, y1 in [(2021, 2035), (2036, 2060), (2061, 2099)]:
                    r = change_corr(g[(r_, s)], air[s], y0, y1)
                    rows.append(dict(depth=dep, a=f"{r_} {s}", b=f"model air (5modelAvg) {s}", period=f"{y0}-{y1}",
                                     median_r=np.nanmedian(r), share_r_above_0p9=np.nanmean(r > 0.9)))
        for y0, y1 in [(2021, 2035), (2036, 2060)]:
            r = change_corr(air["rcp45"], air["rcp85"], y0, y1)
            rows.append(dict(depth="air", a="model air rcp45", b="model air rcp85", period=f"{y0}-{y1}",
                             median_r=np.nanmedian(r), share_r_above_0p9=np.nanmean(r > 0.9)))
    pd.DataFrame(rows).to_csv(OUT / "shared_forcing.csv", index=False)
    print("startup done", flush=True)


def bias():
    from scipy.stats import spearmanr
    import pandas as pd
    cols, rmask = domain()
    rows, lvl, grids = [], [], {}
    esa_ref = {v: esa(v, *ESA_REF, cols) for v in DEP_ESA.values()}
    esa_late = {v: esa(v, 2021, 2023, cols) for v in DEP_ESA.values()}
    for scen in SCENS:
        for base in (BASE, BASE2):
            bridge = maat(scen, *base, cols) - maat(scen, *ESA_REF, cols)
            for run in RUNS:
                for dep, ev in DEP_ESA.items():
                    gb = gipl(run, scen, dep, *base, cols)
                    off = gb - esa_ref[ev]
                    exc = off - bridge
                    su = gipl(run, scen, dep, 2021, 2023, cols) - esa_late[ev]
                    if run == "5ModelAvg":
                        grids[f"excess_{scen}_{dep}_{base[0]}"] = exc
                    for k, rn in REGIONS.items():
                        m = rmask[k] & np.isfinite(exc)
                        rows.append(dict(scen=scen, base=f"{base[0]}-{base[1]}", run=run, depth=dep, esa_var=ev,
                                         region=rn, rho=spearmanr(esa_ref[ev][m][::5], gb[m][::5]).statistic,
                                         raw_offset=np.median(off[m]), bridge=np.median(bridge[m]),
                                         startup_2021_2023_diff=np.nanmedian(su[m]), share_colder=np.mean(exc[m] < 0),
                                         **{f"excess_{kk}": vv for kk, vv in qstats(exc[m]).items()}))
                    if run == "5ModelAvg" and base == BASE:
                        b = np.floor(esa_ref[ev])
                        for lo in range(-10, 5):
                            m = (b == lo) & np.isfinite(exc)
                            if m.sum() >= 200:
                                lvl.append(dict(scen=scen, depth=dep, esa_bin=lo + 0.5, n=int(m.sum()),
                                                excess_median=np.median(exc[m]), p25=np.percentile(exc[m], 25),
                                                p75=np.percentile(exc[m], 75)))
            print(f"bias {scen} {base}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "bias.csv", index=False)
    pd.DataFrame(lvl).to_csv(OUT / "bias_by_level.csv", index=False)
    np.savez_compressed(OUT / "grids_bias.npz", cols=cols, **{k: v.astype("float32") for k, v in grids.items()})


def basestep():
    """Switching GIPL's reference decade from 2026-2035 to 2036-2045 changes a cell's delta-method warming by
    -step, step = GIPL change between the decades minus the model air change between them."""
    import pandas as pd
    cols, rmask = domain()
    rows = []
    for scen in SCENS:
        dair = maat(scen, *BASE2, cols) - maat(scen, *BASE, cols)
        for dep in DEPTHS:
            step = gipl("5ModelAvg", scen, dep, *BASE2, cols) - gipl("5ModelAvg", scen, dep, *BASE, cols) - dair
            for k, rn in REGIONS.items():
                m = rmask[k] & np.isfinite(step)
                rows.append(dict(scen=scen, depth=dep, region=rn, air_change=np.median(dair[m]),
                                 share_abs_above_0p5=np.mean(np.abs(step[m]) > 0.5),
                                 share_abs_above_1=np.mean(np.abs(step[m]) > 1.0),
                                 **{f"step_{kk}": vv for kk, vv in qstats(step[m]).items()}))
    pd.DataFrame(rows).to_csv(OUT / "basestep.csv", index=False)
    print("basestep done", flush=True)


def drift():
    """How much more GIPL warms under RCP 8.5 than RCP 4.5, per degC of extra air warming (2081-2100, from each
    reference decade). 1 = GIPL passes on all extra air warming."""
    import pandas as pd
    cols, rmask = domain()
    rows = []
    for base in (BASE, BASE2):
        dm = {s: maat(s, *LATE, cols) - maat(s, *base, cols) for s in SCENS}
        for dep in DEPTHS:
            dg = {s: gipl("5ModelAvg", s, dep, *LATE, cols) - gipl("5ModelAvg", s, dep, *base, cols) for s in SCENS}
            ex_air, ex_g = dm["rcp85"] - dm["rcp45"], dg["rcp85"] - dg["rcp45"]
            for k, rn in REGIONS.items():
                m = rmask[k] & np.isfinite(ex_g) & np.isfinite(ex_air)
                rows.append(dict(base=f"{base[0]}-{base[1]}", depth=dep, region=rn,
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
    esa_ref = {v: esa(v, *ESA_REF, cols) for v in DEP_ESA.values()}
    for scen in SCENS:
        bridge = maat(scen, *BASE, cols) - maat(scen, *ESA_REF, cols)
        for dep in DEPTHS:
            gm = gipl("5ModelAvg", scen, dep, *MID, cols)
            c_raw = classify(gm)
            grids[f"mid_raw_{scen}_{dep}"] = gm
            c_adj = np.full(cols.size, np.nan, "float32")
            if dep in DEP_ESA:
                adj = esa_ref[DEP_ESA[dep]] + bridge + (gm - gipl("5ModelAvg", scen, dep, *BASE, cols))
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
    for scen in SCENS:
        for y0, y1 in [(2036, 2070), (2026, 2060)]:
            yrs = np.arange(y0, y1 + 1)
            ma = slope(np.asarray(stack(f"maat_{scen}")[y0 - MAAT_YEARS[0]:y1 + 1 - MAAT_YEARS[0]][:, cols],
                                  "float32"), yrs)
            for dep in DEPTHS:
                s = slope(np.asarray(stack(f"gipl_5ModelAvg_{scen}_{dep}")[y0 - YEARS[0]:y1 + 1 - YEARS[0]][:, cols],
                                     "float32"), yrs)
                for k, rn in REGIONS.items():
                    m = rmask[k] & np.isfinite(s) & np.isfinite(ma)
                    rows.append(dict(source="GIPL vs model air", period=f"{y0}-{y1}", scen=scen, depth=dep,
                                     region=rn, ground_trend=np.median(s[m]) * 10, air_trend=np.median(ma[m]) * 10))
    t = pd.DataFrame(rows)
    t["ratio"] = t.ground_trend / t.air_trend
    t.to_csv(OUT / "trends.csv", index=False)
    print("trends done", flush=True)


STAGES = {"prep": prep, "startup": startup, "bias": bias, "basestep": basestep, "drift": drift, "classes": classes,
          "trends": trends}

if __name__ == "__main__":
    for st_ in (["startup", "bias", "basestep", "drift", "classes", "trends"] if sys.argv[1] == "analyze"
                else sys.argv[1:]):
        STAGES[st_]()
