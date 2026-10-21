"""T6b (GIPL_ISSUE_2): independent field observations as a referee between GIPL and ESA CCI.

Stage `boreholes`: UAF Permafrost Lab / GTN-P "Thermal State of Permafrost in North America" daily site records
  (fetch_boreholes.py; June-May years 2015/16-2024/25, US sites). Per site and June-May year: mean annual temperature
  at the surface ("surf" sensor, else a sensor at 0-5 cm), 1 m and 2 m (a sensor within 5 cm of the depth, else linear
  interpolation between the nearest sensors above and below if they are at most 1.5 m apart). A sensor counts only if
  it has >= 330 valid days in the year; daily values outside -50..40 degC are dropped.
  -> <data>/results/t6/borehole_site_years.csv, borehole_sites.csv
Stage `cusp`: CUSP v1.2 (CommUnity near-Surface Permafrost dataset; https://github.com/jonschwenk/cusp), Alaska rows
  from 2000 on. Visual classifications (VI) dropped; a "no permafrost" row counts only if the search reached >= 100 cm
  (obs_limit). Rows grouped into GIPL 1 km cells (EPSG:3338) so dense surveys do not dominate: per cell the share of
  rows with permafrost found, row count, median year, sources.
  -> <data>/results/t6/cusp_cells.csv
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
from pyproj import Transformer

from composite_indexing import config as C

OUT = C.DATA / "results/t6"
TSP = C.DATA / "boreholes/tsp_continuous"
CUSP = C.DATA / "cusp/cusp_v1.2.csv"
TARGETS = {"sfc": 0.0, "d1m": 1.0, "d2m": 2.0}
MIN_DAYS = 330
AK_BOX = dict(lat=(51, 72), lon=(-170, -129))


def to_cell(lon, lat):
    """GIPL 1 km grid row/col and flat index for WGS84 points (NaN-safe: outside -> -1)."""
    x, y = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True).transform(np.asarray(lon), np.asarray(lat))
    col = np.floor((x - C.GIPL_X0) / C.GIPL_RES).astype(int)
    row = (C.GIPL_NY - 1) - np.floor((y - C.GIPL_Y0) / C.GIPL_RES).astype(int)
    ok = (row >= 0) & (row < C.GIPL_NY) & (col >= 0) & (col < C.GIPL_NX)
    return np.where(ok, row, -1), np.where(ok, col, -1), np.where(ok, row * C.GIPL_NX + col, -1)


def sensor_depth(col):
    """'Temp_TMC_+001.00m' -> 1.0; 'Temp_TMC_surf' -> 0.0; air / above-ground sensors -> None."""
    m = re.match(r"Temp_[^_]+_(surf|air|[+-]\d+\.\d+m)$", col.strip(), re.I)
    if not m or m.group(1).lower() == "air":
        return None
    if m.group(1).lower() == "surf":
        return 0.0
    d = float(m.group(1)[:-1])
    return d if d >= 0 else None


def site_year_magt(path):
    df = pd.read_csv(path)
    out, surf_col = {}, None
    sens = {}
    for c in df.columns[1:]:
        d = sensor_depth(c)
        if d is None:
            continue
        v = pd.to_numeric(df[c], errors="coerce")
        v = v.where((v > -50) & (v < 40))
        if v.notna().sum() < MIN_DAYS:
            continue
        if c.strip().lower().endswith("surf"):
            surf_col = float(v.mean())
            continue
        sens.setdefault(round(d, 2), []).append(float(v.mean()))
    depths = np.array(sorted(sens))
    vals = np.array([np.mean(sens[d]) for d in depths])
    for key, z in TARGETS.items():
        if key == "sfc":
            near = vals[depths <= 0.05] if depths.size else []
            out[key] = surf_col if surf_col is not None else (float(np.mean(near)) if len(near) else np.nan)
            continue
        close = np.abs(depths - z) <= 0.05
        if close.any():
            out[key] = float(vals[close].mean())
            continue
        up, dn = depths[depths < z], depths[depths > z]
        if up.size and dn.size and dn[0] - up[-1] <= 1.5:
            a, b = up[-1], dn[0]
            out[key] = float(np.interp(z, [a, b], [vals[depths == a][0], vals[depths == b][0]]))
        else:
            out[key] = np.nan
    out["sensor_depths"] = ";".join(f"{d:g}" for d in depths) + (";surf" if surf_col is not None else "")
    return out


def boreholes():
    OUT.mkdir(parents=True, exist_ok=True)
    rost = []
    for f in sorted(TSP.glob("*/*oster*.csv")):
        r = pd.read_csv(f, encoding="latin-1")
        r.columns = [c.strip() for c in r.columns]
        r["pkg"] = f.parent.name
        rost.append(r)
    rost = pd.concat(rost, ignore_index=True)
    rost = rost[rost.SiteCode.astype(str).str.startswith("US_")]
    sites = (rost.sort_values("pkg").groupby("SiteCode")
             .agg(name=("SiteName", "last"), lat=("Latitude", "last"), lon=("Longitude", "last"),
                  install=("InstallationType", lambda s: ";".join(sorted(set(map(str, s))))),
                  vegetation=("SiteVegetation", "last")).reset_index().rename(columns={"SiteCode": "site"}))
    rows = []
    for f in sorted(TSP.glob("*/US_*_daily.csv")):
        m = re.match(r"^(US_.{3}_\d{3})_(\d{4})_(\d{2})_(\d{2})_(\d{4})_(\d{2})_(\d{2})", f.name)
        if not m:
            continue
        r = site_year_magt(f)
        rows.append(dict(site=m.group(1), pkg=f.parent.name, start=f"{m.group(2)}-{m.group(3)}-{m.group(4)}",
                         end=f"{m.group(5)}-{m.group(6)}-{m.group(7)}", **r))
    sy = pd.DataFrame(rows)
    sy = sy[sy[list(TARGETS)].notna().any(axis=1)]
    t0, t1 = pd.to_datetime(sy.start), pd.to_datetime(sy.end)
    keep = (t1 - t0).dt.days <= 400  # one June-May year per record (a few files span several years)
    sy, mid = sy[keep].copy(), (t0 + (t1 - t0) / 2)[keep]
    sy["hy"] = np.where(mid.dt.month >= 6, mid.dt.year, mid.dt.year - 1)  # year in which the June-May year starts
    # the 2024/25 package republishes full histories for some sites: one row per site and year (mean of copies)
    sy = (sy.groupby(["site", "hy"]).agg(pkg=("pkg", "first"), start=("start", "first"), end=("end", "first"),
                                          sfc=("sfc", "mean"), d1m=("d1m", "mean"), d2m=("d2m", "mean"),
                                          sensor_depths=("sensor_depths", "first"), copies=("pkg", "size"))
          .reset_index())
    sy.to_csv(OUT / "borehole_site_years.csv", index=False)
    sites = sites[sites.site.isin(sy.site)].copy()
    sites.loc[sites.lon > 0, "lon"] *= -1  # one roster entry (US_GS__008) has the sign of its longitude dropped
    sites["row"], sites["col"], sites["cell"] = to_cell(sites.lon.values, sites.lat.values)
    n = sy.groupby("site").agg(n_years=("hy", "nunique"), year_min=("hy", "min"), year_max=("hy", "max"),
                               **{f"n_{k}": (k, "count") for k in TARGETS})
    sites = sites.merge(n, on="site")
    sites.to_csv(OUT / "borehole_sites.csv", index=False)
    print(f"{len(sy)} site-years with a usable depth at {sites.site.nunique()} sites; "
          f"site-years with sfc / 1 m / 2 m: {sy.sfc.notna().sum()} / {sy.d1m.notna().sum()} / {sy.d2m.notna().sum()}")
    print(sites.to_string(index=False))


def cusp():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(CUSP, parse_dates=["date"], low_memory=False)
    d = d[d.lat.between(*AK_BOX["lat"]) & d.lon.between(*AK_BOX["lon"]) & (d.date.dt.year >= 2000)].copy()
    fl = d.quality_flags.fillna("").str.split(";")
    d = d[~fl.map(lambda f: "VI" in f)]
    d = d[(d.pf_observed == 1) | (d.obs_limit >= 100)]
    d["row"], d["col"], d["cell"] = to_cell(d.lon.values, d.lat.values)
    d = d[d.cell >= 0]
    d["year"] = d.date.dt.year
    g = d.groupby("cell")
    cells = pd.DataFrame(dict(
        row=g.row.first(), col=g.col.first(), lat=g.lat.mean(), lon=g.lon.mean(), n_obs=g.size(),
        pf_share=g.pf_observed.mean(), year_median=g.year.median().round().astype(int), year_min=g.year.min(),
        year_max=g.year.max(), pf_depth_median=g.pf_depth.median(),
        sources=g.source.agg(lambda s: ";".join(sorted(set(s)))))).reset_index()
    cells.to_csv(OUT / "cusp_cells.csv", index=False)
    print(f"{len(d)} CUSP rows in {len(cells)} GIPL cells; cells with permafrost in most rows: "
          f"{(cells.pf_share >= 0.5).sum()}, without: {(cells.pf_share < 0.5).sum()}")


def compare():
    """Needs the t6 stacks (t6_gipl_levels.py prep). GIPL comparisons only on good cells (class 1 or 2).
    GIPL has no usable years before 2026 (start-up), so for an observation year y GIPL's implied value is
    GIPL 2026-2035 - (model MAAT 2026-2035 - model MAAT around y): the same bridge as in ESA_GIPL_SPLICING.md.
    -> borehole_compare.csv (site x depth), cusp_compare.csv (cell table), cusp_skill.csv (skill per predictor)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from t6_gipl_levels import BASE, BASE2, MAAT_YEARS, OBS_YEARS, OUT as T6, YEARS, classify, stack

    z = np.load(T6 / "cells.npz")
    idx, cls = z["idx"], z["cls"]

    def col_of(cell):
        k = np.searchsorted(idx, cell)
        k = np.clip(k, 0, idx.size - 1)
        return np.where((cell >= 0) & (idx[k] == cell), k, -1)

    def win(st, first, cols, y0, y1):
        a = np.asarray(st[y0 - first: y1 - first + 1][:, cols], "float32")
        return np.nanmean(a, 0)

    deps = {"sfc": "magtsurface", "d1m": "magt1m", "d2m": "magt2m"}
    scen = "rcp85"  # base period differs by < 0.1 degC between RCPs
    g_base = {k: win(stack(f"gipl_5ModelAvg_{scen}_{d}"), YEARS[0], slice(None), *BASE) for k, d in deps.items()}
    g_base["d05"] = win(stack(f"gipl_5ModelAvg_{scen}_magt0.5m"), YEARS[0], slice(None), *BASE)
    deps2 = {**deps, "d05": "magt0.5m"}
    g_base2 = {k: win(stack(f"gipl_5ModelAvg_{scen}_{d}"), YEARS[0], slice(None), *BASE2) for k, d in deps2.items()}
    g_all = {k: stack(f"gipl_5ModelAvg_{scen}_{d}") for k, d in deps.items()}
    m_all = np.asarray(stack(f"maat_{scen}"), "float32")
    m_base = m_all[BASE[0] - MAAT_YEARS[0]: BASE[1] - MAAT_YEARS[0] + 1].mean(0)
    m_base2 = m_all[BASE2[0] - MAAT_YEARS[0]: BASE2[1] - MAAT_YEARS[0] + 1].mean(0)
    e_all = {v: np.asarray(stack(f"esa_{v}"), "float32") for v in ["GST", "T1m", "T2m", "PFR"]}
    ev = {"sfc": "GST", "d1m": "T1m", "d2m": "T2m"}

    def maat_years(c, years):
        ys = [y for y in years if MAAT_YEARS[0] <= y <= MAAT_YEARS[-1]] or list(range(2006, 2011))
        return m_all[np.array(ys) - MAAT_YEARS[0], c].mean(0)

    def esa_years(var, c, years):
        ys = [y for y in years if OBS_YEARS[0] <= y <= OBS_YEARS[-1]]
        return e_all[var][np.array(ys) - OBS_YEARS[0], c].mean(0) if ys else np.nan

    # --- boreholes: temperature levels -----------------------------------------------------------------------------
    sites = pd.read_csv(OUT / "borehole_sites.csv")
    sy = pd.read_csv(OUT / "borehole_site_years.csv")
    sites["colk"] = col_of(sites.cell.values)
    rows = []
    for _, s in sites[sites.colk >= 0].iterrows():
        c = int(s.colk)
        for _, r in sy[sy.site == s.site].iterrows():
            cal = [int(r.hy), int(r.hy) + 1]  # the two calendar years a June-May year spans
            for k in deps:
                if not np.isfinite(r[k]):
                    continue
                e = esa_years(ev[k], c, cal)
                bridge = m_base[c] - maat_years(c, cal)
                bridge2 = m_base2[c] - maat_years(c, cal)
                same = [y for y in cal if y >= YEARS[0]]  # GIPL as delivered for the same years (start-up only)
                g_same = (float(np.mean([g_all[k][y - YEARS[0], c] for y in same])) if len(same) == len(cal)
                          else np.nan)
                rows.append(dict(site=s.site, name=s["name"], lat=s.lat, lon=s.lon, gipl_class=int(cls[c]),
                                 hy=int(r.hy), depth=k, obs=r[k], esa=e, gipl_base=g_base[k][c], bridge=bridge,
                                 gipl_implied=g_base[k][c] - bridge, gipl_implied2=g_base2[k][c] - bridge2,
                                 gipl_same_year=g_same))
    b = pd.DataFrame(rows)
    b.to_csv(OUT / "borehole_compare_years.csv", index=False)
    site_mean = (b.groupby(["site", "name", "lat", "lon", "gipl_class", "depth"])
                 .agg(n_years=("hy", "nunique"), obs=("obs", "mean"), esa=("esa", "mean"),
                      gipl_base=("gipl_base", "mean"), gipl_implied=("gipl_implied", "mean"),
                      gipl_implied2=("gipl_implied2", "mean"),
                      bridge=("bridge", "mean")).reset_index())
    site_mean.to_csv(OUT / "borehole_compare.csv", index=False)
    good = site_mean[site_mean.gipl_class.isin([1, 2])]
    print("Boreholes (site means), good GIPL cells; error = dataset - observed:")
    for k in deps:
        g = good[(good.depth == k) & good.esa.notna() & good.gipl_implied.notna()]
        if len(g):
            print(f"  {k}: n={len(g)} sites | ESA error median {np.median(g.esa - g.obs):+.2f} "
                  f"(MAE {np.mean(np.abs(g.esa - g.obs)):.2f}) | GIPL error median "
                  f"{np.median(g.gipl_implied - g.obs):+.2f} (MAE {np.mean(np.abs(g.gipl_implied - g.obs)):.2f}) | "
                  f"GIPL (2036-2045 ref.) error median {np.median(g.gipl_implied2 - g.obs):+.2f} | GIPL 2026-2035 "
                  f"as delivered (no warming adjustment) {np.median(g.gipl_base - g.obs):+.2f}")
    sy_ = b[b.gipl_class.isin([1, 2]) & b.gipl_same_year.notna()]
    for k in deps:
        g = sy_[sy_.depth == k]
        if len(g):
            print(f"  {k}: GIPL start-up years vs same-year observations: {len(g)} site-years at {g.site.nunique()} "
                  f"sites, median error {np.median(g.gipl_same_year - g.obs):+.2f}, ESA {np.nanmedian(g.esa - g.obs):+.2f}")

    # --- CUSP: permafrost found / not found ------------------------------------------------------------------------
    cc = pd.read_csv(OUT / "cusp_cells.csv")
    cc["colk"] = col_of(cc.cell.values)
    cc = cc[cc.colk >= 0].copy()
    cc["gipl_class"] = cls[cc.colk.values]
    out = {k: [] for k in ["esa_sfc", "esa_d1m", "esa_d2m", "esa_pfr", "bridge", "bridge2"]}
    for _, r in cc.iterrows():
        c, y = int(r.colk), int(r.year_median)
        years = list(range(y - 2, y + 3))
        for k in deps:
            out[f"esa_{k}"].append(esa_years(ev[k], c, years))
        out["esa_pfr"].append(esa_years("PFR", c, years))
        out["bridge"].append(m_base[c] - maat_years(c, years))
        out["bridge2"].append(m_base2[c] - maat_years(c, years))
    for k, v in out.items():
        cc[k] = v
    for k in ["sfc", "d05", "d1m", "d2m"]:
        cc[f"gipl_raw_{k}"] = g_base[k][cc.colk.values]
        cc[f"gipl_implied_{k}"] = cc[f"gipl_raw_{k}"] - cc.bridge
        cc[f"gipl_implied2_{k}"] = g_base2[k][cc.colk.values] - cc.bridge2
    cc["pf_obs"] = (cc.pf_share >= 0.5).astype(int)
    cc.to_csv(OUT / "cusp_compare.csv", index=False)

    preds = ([f"esa_{k}" for k in deps] + [f"gipl_raw_{k}" for k in ["sfc", "d05", "d1m", "d2m"]]
             + [f"gipl_implied_{k}" for k in ["sfc", "d05", "d1m", "d2m"]]
             + [f"gipl_implied2_{k}" for k in ["sfc", "d05", "d1m", "d2m"]])
    ok = cc.gipl_class.isin([1, 2]) & cc[preds + ["esa_pfr"]].notna().all(axis=1)
    d = cc[ok]
    rows = []
    y = d.pf_obs.values
    for p in preds:
        t = d[p].values
        cl = classify(t)
        thr = np.arange(-6, 4.01, 0.1)
        bacc = [0.5 * (np.mean(t[y == 1] <= th) + np.mean(t[y == 0] > th)) for th in thr]
        rows.append(dict(predictor=p, n=len(d), n_pf=int(y.sum()), n_nopf=int((y == 0).sum()),
                         auc=auc(-t, y), miss_rate_0C=np.mean(t[y == 1] > 0), false_frozen_0C=np.mean(t[y == 0] <= 0),
                         bal_acc_0C=0.5 * (np.mean(t[y == 1] <= 0) + np.mean(t[y == 0] > 0)),
                         best_threshold=thr[int(np.argmax(bacc))], best_bal_acc=max(bacc),
                         median_pf=np.median(t[y == 1]), median_nopf=np.median(t[y == 0]),
                         **{f"pf_class{i}": np.mean(cl[y == 1] == i) for i in range(3)},
                         **{f"nopf_class{i}": np.mean(cl[y == 0] == i) for i in range(3)}))
    pfr = d.esa_pfr.values
    rows.append(dict(predictor="esa_pfr (>= 50 %)", n=len(d), n_pf=int(y.sum()), n_nopf=int((y == 0).sum()),
                     auc=auc(pfr, y), bal_acc_0C=0.5 * (np.mean(pfr[y == 1] >= 50) + np.mean(pfr[y == 0] < 50))))
    sk = pd.DataFrame(rows)
    sk.to_csv(OUT / "cusp_skill.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(sk.round(3).to_string(index=False))


def auc(score, y):
    """Area under the ROC curve via the rank-sum (Mann-Whitney) statistic."""
    from scipy.stats import rankdata
    r = rankdata(score)
    n1, n0 = (y == 1).sum(), (y == 0).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


if __name__ == "__main__":
    {"boreholes": boreholes, "cusp": cusp, "compare": compare}[sys.argv[1]]()
