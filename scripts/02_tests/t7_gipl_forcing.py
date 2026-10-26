"""T7 (GIPL forcing): which SNAP air temperature product drove GIPL 2.0? The docs compare GIPL with SNAP's 2 km
CMIP5 air temperature; SNAP also publishes the same CMIP5 runs at 771 m (PRISM 1971-2000 base instead of 1961-1990).
The GIPL 2.0 paper (Marchenko et al., ICOP 2024) only says "SNAP ... CMIP5 ... scaled down to 1 km".

Stage `prep <key>` (slurm/19, one array task per source): air temperature on every valid GIPL cell (t6 cells.npz),
read straight from SNAP's zips (READ-ONLY, GDAL /vsizip/, no sidecar files) or the local 2 km copies.
  <data>/results/t7/air_<key>.npy   float16 (nyear, ncell) calendar-year mean of 12 monthly files; value of the source
                                     cell under the GIPL cell centre (2 km: parent cell; 771 m: cell under the centre)
  <data>/results/t7/airm_<key>.npy  float16 (nyear * 12, nsub) monthly values on the sampled cells (every 10th domain cell)
Sources: CMIP5 2006-2100 at 771 m and 2 km for each GIPL run (5ModelAvg, GFDL-CM3, NCAR-CCSM4; RCP 4.5 / 8.5);
wildcards: CRU TS 3.1 771 m (1901-2009), CRU TS 4.08 2 km (1901-2023), CMIP3 5-model average 771 m (A1B, A2).

Stage `analyze` (slurm/20): CSVs in <data>/results/t7/
  mask.csv      GIPL land mask vs the 771 m and 2 km masks at GIPL cell centres
  pairs.csv     neighbouring GIPL cells sharing / not sharing a 2 km parent cell (block fingerprint), and 771 m index gaps
  highpass.csv  fine-scale (minus local mean) GIPL surface vs fine-scale 771 m / 2 km air, with partial correlations
  yty.csv       per-cell correlation of year-to-year changes, GIPL run vs its own model's air at 771 m and 2 km
  lagscan.csv   same, against every source and time offset (GIPL year y vs source year y - offset)
  season.csv    GIPL surface year-to-year changes vs air averaged over different months / year definitions
  levels.csv    771 m minus 2 km air temperature (same model and scenario) and expected-warming difference
"""
import os
import sys
import time
from pathlib import Path

os.environ["GDAL_PAM_ENABLED"] = "NO"  # never write .aux.xml next to SNAP's read-only files

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import rasterio

from composite_indexing import config as C

T6 = C.DATA / "results/t6"
OUT = C.DATA / "results/t7"
RUNS = ["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"]
SCENS = ["rcp45", "rcp85"]
YEARS = np.arange(2021, 2121)
REGIONS = {0: "Statewide", 1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
SNAP = Path("/import/SNAP/poseidon/CKAN/CKAN_Data/Base")
Z771 = SNAP / "AK_771m/projected/AR5_CMIP5_models/Projected_Monthly_and_Derived_Temperature_Products_771m_CMIP5_AR5/monthly"
Z2K = SNAP / "AK_CAN_2km/projected/AR5_CMIP5_models/Projected_Monthly_and_Derived_Temperature_Products_2km_CMIP5_AR5/monthly"
ZCRU = SNAP / ("AK_771m/historical/CRU_TS/Historical_Monthly_and_Derived_Temperature_Products_771m_CRU_TS/"
               "tas_AK_771m_CRU_TS31_historical.zip")
ZAR4 = SNAP / "AK_771m/projected/AR4_CMIP3_models/Projected_Monthy_and_Derived_Temperature_Products_771m_CMIP3_AR4/monthly"
TAS_NAME = {"5ModelAvg": "5modelAvg", "GFDL-CM3": "GFDL-CM3", "NCAR-CCSM4": "CCSM4"}


def sources():
    """key -> (years, path(month, year))."""
    s = {}
    for run in RUNS:
        m = TAS_NAME[run]
        for scen in SCENS:
            name = f"tas_mean_C_AR5_{m}_{scen}_{{mo:02d}}_{{y}}.tif"
            s[f"771_{run}_{scen}"] = (np.arange(2006, 2101), lambda mo, y, z=f"/vsizip/{Z771}/tas_mean_C_AK_AR5_{m}_{scen}"
                                      f"_01_2006-12_2100.zip/tas/" + name: z.format(mo=mo, y=y))
            if run == "5ModelAvg":
                z2 = str(C.DATA / f"tas_tif/5modelAvg_{scen}") + "/" + name
            else:
                z2 = f"/vsizip/{Z2K}/tas_mean_C_AK_CAN_AR5_{m}_{scen}_01_2006-12_2100.zip/tas/" + name
            s[f"2k_{run}_{scen}"] = (np.arange(2006, 2101), lambda mo, y, z=z2: z.format(mo=mo, y=y))
    s["771_cru31"] = (np.arange(1901, 2010), lambda mo, y: f"/vsizip/{ZCRU}/tas/tas_mean_C_cru_TS31_{mo:02d}_{y}.tif")
    s["2k_cru408"] = (np.arange(1901, 2024), lambda mo, y: str(
        C.DATA / f"tas_tif/cru_ts408/tas_mean_C_cru_ts408_historical_{mo:02d}_{y}.tif"))
    for sc, y1 in [("sresa1b", 2100), ("sresa2", 2099)]:
        s[f"771_ar4_{sc}"] = (np.arange(2001, y1 + 1), lambda mo, y, sc=sc: f"/vsizip/{ZAR4}/tas_AK_771m_5modelAvg_{sc}.zip"
                              f"/tas/tas_mean_C_ar4_5modelAvg_{sc}_{mo:02d}_{y}.tif")
    return s


SRC = sources()


def cells():
    z = np.load(T6 / "cells.npz")
    dom = np.flatnonzero((z["cls"] == 2) & (z["pfr_2023"] > 0))
    return z, dom, dom[::10]


def lookup(t, shape, x, y):
    """Row / column of the source cell under each (x, y); -1 outside the grid."""
    j = np.floor((x - t.c) / t.a).astype(int)
    i = np.floor((y - t.f) / t.e).astype(int)
    ok = (i >= 0) & (i < shape[0]) & (j >= 0) & (j < shape[1])
    return np.where(ok, i, -1), np.where(ok, j, -1)


def sample(path, x, y, cache):
    with rasterio.open(path) as s:
        key = (tuple(s.transform), s.shape)
        if key not in cache:
            cache[key] = lookup(s.transform, s.shape, x, y)
        a = s.read(1)
    i, j = cache[key]
    v = np.full(x.size, np.nan, "float32")
    ok = i >= 0
    v[ok] = a[i[ok], j[ok]]
    v[(v < -1000) | (v > 1000)] = np.nan
    return v


def save(path, a):
    tmp = path.with_suffix(".part")
    with open(tmp, "wb") as f:
        np.save(f, a)
    os.replace(tmp, path)


def prep(key):
    OUT.mkdir(parents=True, exist_ok=True)
    pa, pm = OUT / f"air_{key}.npy", OUT / f"airm_{key}.npy"
    if pa.exists() and pm.exists():
        return
    z, dom, sub = cells()
    x, y = z["x"], z["y"]
    years, path = SRC[key]
    ann = np.full((years.size, x.size), np.nan, "float16")
    mon = np.full((years.size * 12, sub.size), np.nan, "float16")
    cache, t0 = {}, time.time()
    for k, yr in enumerate(years):
        acc = np.zeros(x.size, "float32")
        for mo in range(1, 13):
            v = sample(path(mo, yr), x, y, cache)
            acc += v
            mon[k * 12 + mo - 1] = v[sub]
        ann[k] = acc / 12
        if yr % 10 == 0:
            print(f"{key} {yr} ({time.time() - t0:.0f} s)", flush=True)
    save(pm, mon)
    save(pa, ann)
    print(f"{key} done ({time.time() - t0:.0f} s); grids {list(cache)}", flush=True)


# ---------------------------------------------------------------------------------------------------------------------
def air(key, cols, y0=None, y1=None):
    years = SRC[key][0]
    a = np.load(OUT / f"air_{key}.npy", mmap_mode="r")
    if y0 is None:
        return np.asarray(a[:, cols], "float32")
    if y0 < years[0] or y1 > years[-1]:
        return None
    return np.asarray(a[y0 - years[0]:y1 + 1 - years[0]][:, cols], "float32")


def gipl(run, scen, dep, cols, y0, y1):
    a = np.load(T6 / f"gipl_{run}_{scen}_{dep}.npy", mmap_mode="r")
    return np.asarray(a[y0 - YEARS[0]:y1 + 1 - YEARS[0]][:, cols], "float32")


def dcorr(a, b):
    """Per-cell correlation of year-to-year changes of two (year, cell) arrays of equal length."""
    da, db = np.diff(a, axis=0), np.diff(b, axis=0)
    da, db = da - da.mean(0), db - db.mean(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (da * db).sum(0) / np.sqrt((da ** 2).sum(0) * (db ** 2).sum(0))


def grid2d(vals, z):
    g = np.full(int(np.prod(z["shape"])), np.nan, "float32")
    g[z["idx"]] = vals
    return g.reshape(z["shape"])


def gipl_centres():
    with rasterio.open(C.DATA / "gipl_tif/magtsurface/gipl_5ModelAvg_rcp45_magtsurface_degC_2050.tif") as s:
        t, g = s.transform, s.read(1)
    xs = t.c + (np.arange(g.shape[1]) + 0.5) * t.a
    ys = t.f + (np.arange(g.shape[0]) + 0.5) * t.e
    return xs, ys, g


def mask():
    import pandas as pd
    xs, ys, g = gipl_centres()
    X, Y = np.meshgrid(xs, ys)
    gv = g > -9000
    rows = []
    for key in ["771_5ModelAvg_rcp45", "2k_5ModelAvg_rcp45"]:
        a = sample(SRC[key][1](1, 2050), X.ravel(), Y.ravel(), {}).reshape(X.shape)
        av = np.isfinite(a)
        rows.append(dict(source=key, gipl_valid=int(gv.sum()), both=int((gv & av).sum()),
                         gipl_only=int((gv & ~av).sum()), source_only=int((~gv & av).sum())))
    pd.DataFrame(rows).to_csv(OUT / "mask.csv", index=False)
    print(pd.DataFrame(rows).to_string(), flush=True)


def pairs():
    """Neighbouring GIPL cells: |difference| when the pair shares a 2 km parent cell vs not, and when their 771 m cells
    are adjacent vs one apart. Nearest-neighbour forcing from a grid leaves its block pattern in GIPL."""
    import pandas as pd
    z, dom, sub = cells()
    ok = np.isin(z["cls"], [1, 2])
    fields = {"GIPL surface": np.nanmean(gipl("5ModelAvg", "rcp45", "magtsurface", np.arange(z["idx"].size), 2036, 2065), 0),
              "GIPL 1 m": np.nanmean(gipl("5ModelAvg", "rcp45", "magt1m", np.arange(z["idx"].size), 2036, 2065), 0),
              "air 771 m": np.nanmean(air("771_5ModelAvg_rcp45", slice(None), 2036, 2065), 0),
              "air 2 km": np.nanmean(air("2k_5ModelAvg_rcp45", slice(None), 2036, 2065), 0)}
    xs, ys, _ = gipl_centres()
    r0, c0 = np.unravel_index(z["idx"][:1000], tuple(z["shape"]))
    assert np.allclose(xs[c0], z["x"][:1000]) and np.allclose(ys[r0], z["y"][:1000])
    with rasterio.open(SRC["771_5ModelAvg_rcp45"][1](1, 2050)) as s:
        t7 = s.transform
    p2x, p2y = np.floor((xs - C.TAS_X0) / C.TAS_RES), np.floor((ys - C.TAS_Y0) / C.TAS_RES)
    q7x, q7y = np.floor((xs - t7.c) / t7.a), np.floor((ys - t7.f) / t7.e)
    rows = []
    for name, f in fields.items():
        g = grid2d(np.where(ok, f, np.nan), z)
        for axis, p2, q7 in [("east-west", p2x, q7x), ("north-south", p2y, q7y)]:
            if axis == "east-west":
                d = np.abs(g[:, 1:] - g[:, :-1])
                same, gap = np.broadcast_to(p2[1:] == p2[:-1], d.shape), np.broadcast_to(np.abs(q7[1:] - q7[:-1]), d.shape)
            else:
                d = np.abs(g[1:] - g[:-1])
                same = np.broadcast_to((p2[1:] == p2[:-1])[:, None], d.shape)
                gap = np.broadcast_to(np.abs(q7[1:] - q7[:-1])[:, None], d.shape)
            v = np.isfinite(d)
            r = dict(field=name, axis=axis, n_pairs=int(v.sum()),
                     same_2km_parent=np.median(d[v & same]), different_2km_parent=np.median(d[v & ~same]),
                     adjacent_771=np.median(d[v & (gap == 1)]), skip_one_771=np.median(d[v & (gap == 2)]))
            r["ratio_2km"] = r["different_2km_parent"] / r["same_2km_parent"]
            r["ratio_771"] = r["skip_one_771"] / r["adjacent_771"]
            rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "pairs.csv", index=False)
    print(t.to_string(), flush=True)


def highpass():
    import pandas as pd
    from scipy.ndimage import uniform_filter
    z, dom, sub = cells()
    allc = np.arange(z["idx"].size)
    ok = np.isin(z["cls"], [1, 2])
    rows = []
    for scen in SCENS:
        f = {"g": np.nanmean(gipl("5ModelAvg", scen, "magtsurface", allc, 2036, 2065), 0),
             "a7": np.nanmean(air(f"771_5ModelAvg_{scen}", slice(None), 2036, 2065), 0),
             "a2": np.nanmean(air(f"2k_5ModelAvg_{scen}", slice(None), 2036, 2065), 0)}
        for w in (3, 5, 9):
            hp = {}
            for k, v in f.items():
                g = grid2d(np.where(ok, v, np.nan), z)
                m = np.isfinite(g)
                num = uniform_filter(np.where(m, g, 0), w, mode="constant")
                den = uniform_filter(m.astype("float32"), w, mode="constant")
                with np.errstate(invalid="ignore", divide="ignore"):
                    hp[k] = (g - num / den).ravel()[z["idx"]]
            for reg, rn in REGIONS.items():
                sel = np.zeros(z["idx"].size, bool)
                sel[dom] = True
                if reg:
                    sel &= z["region"] == reg
                sel &= np.isfinite(hp["g"]) & np.isfinite(hp["a7"]) & np.isfinite(hp["a2"])
                c = np.corrcoef([hp["g"][sel], hp["a7"][sel], hp["a2"][sel]])
                r_g7, r_g2, r_72 = c[0, 1], c[0, 2], c[1, 2]
                rows.append(dict(scen=scen, window_km=w, region=rn, n=int(sel.sum()), r_gipl_771=r_g7, r_gipl_2km=r_g2,
                                 r_771_2km=r_72,
                                 partial_gipl_771_given_2km=(r_g7 - r_g2 * r_72) / np.sqrt((1 - r_g2 ** 2) * (1 - r_72 ** 2)),
                                 partial_gipl_2km_given_771=(r_g2 - r_g7 * r_72) / np.sqrt((1 - r_g7 ** 2) * (1 - r_72 ** 2))))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "highpass.csv", index=False)
    print(t[t.region == "Statewide"].to_string(), flush=True)


def yty():
    import pandas as pd
    z, dom, sub = cells()
    rows = []
    for run in RUNS:
        for scen in SCENS:
            for dep in ["magtsurface", "magt1m"]:
                for y0, y1 in [(2021, 2035), (2036, 2060), (2061, 2099)]:
                    g = gipl(run, scen, dep, sub, y0, y1)
                    for res in ["771", "2k"]:
                        r = dcorr(g, air(f"{res}_{run}_{scen}", sub, y0, y1))
                        rows.append(dict(run=run, scen=scen, depth=dep, period=f"{y0}-{y1}", air=f"{res} own model",
                                         median_r=np.nanmedian(r), share_r_above_0p5=np.nanmean(r > 0.5)))
    for run in RUNS:  # the two air products against each other
        for scen in SCENS:
            r = dcorr(air(f"771_{run}_{scen}", sub, 2021, 2099), air(f"2k_{run}_{scen}", sub, 2021, 2099))
            rows.append(dict(run=run, scen=scen, depth="air", period="2021-2099", air="771 vs 2k",
                             median_r=np.nanmedian(r), share_r_above_0p5=np.nanmean(r > 0.5)))
    e = np.load(T6 / "esa_GST.npy", mmap_mode="r")  # benchmark: observed ground surface vs observed air, 2003-2023
    esa = np.asarray(e[3:][:, sub], "float32")
    for key in ["2k_cru408"]:
        r = dcorr(esa, air(key, sub, 2003, 2023))
        rows.append(dict(run="ESA GST", scen="obs", depth="magtsurface", period="2003-2023", air=key,
                         median_r=np.nanmedian(r), share_r_above_0p5=np.nanmean(r > 0.5)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "yty.csv", index=False)
    print(t.to_string(), flush=True)


def lagscan():
    import pandas as pd
    z, dom, sub = cells()
    cols = sub[::2]
    rows = []
    t0 = time.time()
    for run in RUNS:
        for scen in SCENS:
            for y0, y1 in [(2021, 2035), (2036, 2095)]:
                g = gipl(run, scen, "magtsurface", cols, y0, y1)
                for key, (yrs, _) in SRC.items():
                    a = air(key, cols)
                    for off in range(y0 - yrs[-1] + (y1 - y0), y0 - yrs[0] + 1):
                        s0 = y0 - off - yrs[0]
                        r = dcorr(g, a[s0:s0 + y1 - y0 + 1])
                        rows.append(dict(run=run, scen=scen, window=f"{y0}-{y1}", source=key, offset=off,
                                         source_years=f"{y0 - off}-{y1 - off}", median_r=np.nanmedian(r)))
                print(f"lagscan {run} {scen} {y0}-{y1} ({time.time() - t0:.0f} s)", flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "lagscan.csv", index=False)
    best = t.loc[t.groupby(["run", "scen", "window", "source"]).median_r.idxmax()]
    print(best.sort_values(["run", "scen", "window", "median_r"], ascending=[1, 1, 1, 0])
          .groupby(["run", "scen", "window"]).head(4).to_string(), flush=True)


def season():
    import pandas as pd
    z, dom, sub = cells()
    y0, y1 = 2036, 2095
    # GIPL 2.0 runs August to August (2010 GIPL/SNAP presentation, input dialog), so test Aug-Jul years too
    defs = {"Jan-Dec": (0, range(0, 12)), "Aug-Jul (ends in year)": (-1, range(7, 19)),
            "Aug-Jul (starts in year)": (0, range(7, 19)), "Jul-Jun (ends in year)": (-1, range(6, 18)),
            "Oct-Sep (ends in year)": (-1, range(9, 21)), "Nov-Mar (ends in year)": (-1, range(10, 15)),
            "Nov-Mar (starts in year)": (0, range(10, 15)), "May-Sep": (0, range(4, 9)), "Jun-Aug": (0, range(5, 8)),
            "Dec-Feb (ends in year)": (-1, range(11, 14))}
    rows = []
    for (run, scen), off in OFFSET.items():  # GIPL year y vs air year y - off
        g = gipl(run, scen, "magtsurface", sub, y0, y1)
        for res in ["771", "2k"]:
            key = f"{res}_{run}_{scen}"
            yrs = SRC[key][0]
            flat = np.asarray(np.load(OUT / f"airm_{key}.npy", mmap_mode="r"), "float32")  # (year * 12, nsub)
            for name, (shift, months) in defs.items():
                a = np.stack([flat[(y - off - yrs[0] + shift) * 12 + np.array(months)].mean(0) for y in range(y0, y1 + 1)])
                r = dcorr(g, a)
                rows.append(dict(run=run, scen=scen, air=key, offset=off, months=name, median_r=np.nanmedian(r)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "season.csv", index=False)
    print(t.pivot_table(index=["run", "scen", "air"], columns="months", values="median_r").round(2).to_string(), flush=True)


def levels():
    import pandas as pd
    z, dom, sub = cells()
    reg = z["region"][dom]
    rows = []
    for run in RUNS:
        for scen in SCENS:
            a7, a2 = air(f"771_{run}_{scen}", dom), air(f"2k_{run}_{scen}", dom)
            yrs = SRC[f"2k_{run}_{scen}"][0]
            per = {p: (yrs >= p[0]) & (yrs <= p[1]) for p in [(2014, 2023), (2026, 2035), (2036, 2045), (2081, 2100)]}
            for k, rn in REGIONS.items():
                sel = np.ones(dom.size, bool) if k == 0 else reg == k
                r = dict(run=run, scen=scen, region=rn)
                for p, m in per.items():
                    r[f"diff_{p[0]}_{p[1]}"] = np.nanmedian(a7[m][:, sel].mean(0) - a2[m][:, sel].mean(0))
                w7 = a7[per[(2026, 2035)]].mean(0) - a7[per[(2014, 2023)]].mean(0)
                w2 = a2[per[(2026, 2035)]].mean(0) - a2[per[(2014, 2023)]].mean(0)
                r["expected_warming_771"] = np.nanmedian(w7[sel])
                r["expected_warming_2k"] = np.nanmedian(w2[sel])
                r["expected_warming_diff_p10"] = np.nanpercentile((w7 - w2)[sel], 10)
                r["expected_warming_diff_p90"] = np.nanpercentile((w7 - w2)[sel], 90)
                rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "levels.csv", index=False)
    print(t[t.region == "Statewide"].round(2).to_string(), flush=True)


def yearmap():
    """Which forcing year does each GIPL year carry? Spatial correlation (across cells) between GIPL's year-to-year
    change map (surface, year Y vs Y-1) and every source's air temperature change map (year X vs X-1). A year's weather
    pattern is distinctive, so the best match identifies the forcing year."""
    import pandas as pd
    z, dom, sub = cells()
    A, labels = [], []
    for key, (yrs, _) in SRC.items():
        A.append(np.diff(air(key, sub), axis=0))
        labels += [(key, int(y)) for y in yrs[1:]]
    A = np.concatenate(A)
    ok_air = np.all(np.isfinite(A), 0)
    src = np.array([k for k, _ in labels])
    yr = np.array([y for _, y in labels])
    rows, mats = [], {}
    for run in RUNS:
        for scen in SCENS:
            for dep in ["magtsurface", "magt1m"]:
                dg = np.diff(gipl(run, scen, dep, sub, 2021, 2120), axis=0)  # GIPL years 2022-2120
                ok = ok_air & np.all(np.isfinite(dg), 0)
                a, g = A[:, ok], dg[:, ok]
                a = (a - a.mean(1, keepdims=True)) / a.std(1, keepdims=True)
                g = (g - g.mean(1, keepdims=True)) / g.std(1, keepdims=True)
                R = g @ a.T / ok.sum()
                mats[f"{run}_{scen}_{dep}"] = R.astype("float32")
                for k, y in enumerate(range(2022, 2121)):
                    order = np.argsort(R[k])[::-1]
                    j, j2 = order[0], next(i for i in order[1:] if src[i] != src[order[0]] or yr[i] != yr[order[0]])
                    own = {f"r_{s}_minus20": R[k, (src == s) & (yr == y - 20)] for s in
                           ["2k_cru408", f"2k_{run}_{scen}", f"771_{run}_{scen}"]}
                    rows.append(dict(run=run, scen=scen, depth=dep, gipl_year=y, best_source=src[j], best_year=yr[j],
                                     best_offset=y - yr[j], best_r=R[k, j], second_source=src[j2],
                                     second_year=yr[j2], second_r=R[k, j2],
                                     **{k_: (v[0] if v.size else np.nan) for k_, v in own.items()}))
                print(f"yearmap {run} {scen} {dep}", flush=True)
    np.savez_compressed(OUT / "yearmap_R.npz", source=src, year=yr, **mats)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "yearmap.csv", index=False)
    s = t[t.depth == "magtsurface"]
    print(s.groupby(["run", "scen"]).apply(lambda d: d.groupby(["best_source", "best_offset"]).size()
                                            .sort_values(ascending=False).head(6)).to_string(), flush=True)


def bias20():
    """GIPL against ESA, with GIPL's years taken at face value (old excess offset: GIPL 2026-2035 - ESA 2014-2023 -
    model air warming) and on climate years (GIPL climate 2004-2015 = observed weather, vs ESA 2004-2015)."""
    import pandas as pd
    z, dom, sub = cells()
    reg = z["region"][dom]
    cru = air("2k_cru408", dom)
    cru_years = SRC["2k_cru408"][0]
    cw = cru[(cru_years >= 2014) & (cru_years <= 2023)].mean(0) - cru[(cru_years >= 2006) & (cru_years <= 2015)].mean(0)
    rows = []
    for dep, ev in [("magtsurface", "GST"), ("magt1m", "T1m"), ("magt2m", "T2m")]:
        e = np.asarray(np.load(T6 / f"esa_{ev}.npy", mmap_mode="r")[:, dom], "float32")  # 2000-2023
        e0615, e1423 = e[6:16].mean(0), e[14:24].mean(0)
        for run in RUNS:
            for scen in SCENS:
                g = gipl(run, scen, dep, dom, 2026, 2035).mean(0)
                ma = air(f"2k_5ModelAvg_{scen}", dom, 2014, 2035)
                expected = ma[12:].mean(0) - ma[:10].mean(0)
                old = g - e1423 - expected
                off = OFFSET.get((run, scen))
                new = (gipl(run, scen, dep, dom, 2004 + off, 2015 + off).mean(0) - e[2004 - 2000:2016 - 2000].mean(0)
                       if off else np.full_like(g, np.nan))
                for k, rn in REGIONS.items():
                    sel = np.ones(dom.size, bool) if k == 0 else reg == k
                    rows.append(dict(depth=dep, esa=ev, run=run, scen=scen, region=rn,
                                     old_excess_offset=np.nanmedian(old[sel]), old_expected_warming=np.nanmedian(expected[sel]),
                                     offset_years=off, new_offset_vs_esa_same_years=np.nanmedian(new[sel]),
                                     new_share_colder=np.nanmean(new[sel] < 0),
                                     new_p10=np.nanpercentile(new[sel], 10), new_p90=np.nanpercentile(new[sel], 90),
                                     cru_warming_2006_15_to_2014_23=np.nanmedian(cw[sel]),
                                     esa_change_2006_15_to_2014_23=np.nanmedian((e1423 - e0615)[sel])))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "bias20.csv", index=False)
    print(t[t.region == "Statewide"].round(2).to_string(), flush=True)


# GIPL year Y carries the forcing of year Y - offset (lagscan / yearmap): GIPL 2021-2035 = observed CRU 2001-2015,
# GIPL 2036-2120 = CMIP5 2016-2100. GFDL-CM3 RCP 8.5 is one year further along. NCAR-CCSM4: see yearmap.
OFFSET = {("5ModelAvg", "rcp45"): 20, ("5ModelAvg", "rcp85"): 20, ("GFDL-CM3", "rcp45"): 20, ("GFDL-CM3", "rcp85"): 19}


def offsets():
    """Per-cell match at offset 0 (years as labelled) vs the forcing offset; statewide series for figures."""
    import pandas as pd
    z, dom, sub = cells()
    rows, ser = [], []
    for (run, scen), off in OFFSET.items():
        for dep in ["magtsurface", "magt1m", "magt2m"]:
            for (y0, y1), key in [((2021, 2035), "2k_cru408"), ((2036, 2095), f"2k_{run}_{scen}"),
                                  ((2036, 2095), f"771_{run}_{scen}")]:
                g = gipl(run, scen, dep, sub, y0, y1)
                for o in sorted({0, off}):
                    a = air(key, sub, y0 - o, y1 - o)
                    if a is None:
                        continue
                    r = dcorr(g, a)
                    rows.append(dict(run=run, scen=scen, depth=dep, gipl_years=f"{y0}-{y1}", air=key, offset=o,
                                     air_years=f"{y0 - o}-{y1 - o}", median_r=np.nanmedian(r),
                                     p10_r=np.nanpercentile(r, 10), p90_r=np.nanpercentile(r, 90),
                                     share_r_above_0p5=np.nanmean(r > 0.5)))
        g = gipl(run, scen, "magtsurface", sub, 2021, 2120)
        cru, mod = air("2k_cru408", sub), air(f"2k_{run}_{scen}", sub)
        for k, y in enumerate(range(2021, 2121)):
            yc, ym = y - off - 1901, y - off - 2006
            ser.append(dict(run=run, scen=scen, gipl_year=y, forcing_year=y - off, gipl_surface=np.nanmedian(g[k]),
                            cru_air=np.nanmedian(cru[yc]) if 0 <= yc < cru.shape[0] else np.nan,
                            model_air_shifted=np.nanmedian(mod[ym]) if 0 <= ym < mod.shape[0] else np.nan,
                            model_air_same_year=np.nanmedian(mod[y - 2006]) if y <= 2100 else np.nan))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "offsets.csv", index=False)
    pd.DataFrame(ser).to_csv(OUT / "series.csv", index=False)
    print(t.round(2).to_string(), flush=True)


def reinterp():
    """GIPL_ISSUE_2 section 5 numbers redone with the forcing offset: warming rates (GIPL vs air, 5ModelAvg) and the
    share of the extra RCP 8.5 air warming that reaches the ground."""
    import pandas as pd
    z, dom, sub = cells()

    def slope(a):
        x = np.arange(a.shape[0]) - (a.shape[0] - 1) / 2
        return (x[:, None] * (a - a.mean(0))).sum(0) / (x ** 2).sum()

    rows = []
    for label, (gy0, gy1), (ay0, ay1) in [("as labelled", (2036, 2070), (2036, 2070)),
                                          ("shifted 20 yr", (2036, 2070), (2016, 2050)),
                                          ("shifted 20 yr", (2056, 2090), (2036, 2070))]:
        for scen in SCENS:
            a = slope(air(f"2k_5ModelAvg_{scen}", sub, ay0, ay1))
            for dep in ["magtsurface", "magt1m", "magt2m"]:
                g = slope(gipl("5ModelAvg", scen, dep, sub, gy0, gy1))
                rows.append(dict(test="warming rate", years=label, gipl_years=f"{gy0}-{gy1}", air_years=f"{ay0}-{ay1}",
                                 scen=scen, depth=dep, gipl=np.nanmedian(g) * 10, air=np.nanmedian(a) * 10,
                                 ratio=np.nanmedian(g) / np.nanmedian(a)))
    for label, gp, ap in [("as labelled", (2081, 2100), (2081, 2100)), ("shifted 20 yr", (2101, 2120), (2081, 2100))]:
        da = (air("2k_5ModelAvg_rcp85", sub, *ap).mean(0) - air("2k_5ModelAvg_rcp85", sub, 2006, 2015).mean(0)) - \
             (air("2k_5ModelAvg_rcp45", sub, *ap).mean(0) - air("2k_5ModelAvg_rcp45", sub, 2006, 2015).mean(0))
        for dep in ["magtsurface", "magt1m", "magt2m"]:
            g = {s: gipl("5ModelAvg", s, dep, sub, *gp).mean(0) - gipl("5ModelAvg", s, dep, sub, 2026, 2035).mean(0)
                 for s in SCENS}
            dg = g["rcp85"] - g["rcp45"]
            rows.append(dict(test="extra RCP 8.5 warming", years=label, gipl_years=f"{gp[0]}-{gp[1]}",
                             air_years=f"{ap[0]}-{ap[1]}", scen="rcp85-rcp45", depth=dep, gipl=np.nanmedian(dg),
                             air=np.nanmedian(da), ratio=np.nanmedian(dg) / np.nanmedian(da)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "reinterp.csv", index=False)
    print(t.round(2).to_string(), flush=True)


def sites20():
    """GIPL_ISSUE_2 site checks redone with matched climate years: an observation in year y is compared with GIPL year
    y + 20 (5ModelAvg), instead of GIPL 2026-2035 minus a model-air bridge. Reads the t6b tables (t6b_sites.py)."""
    import pandas as pd
    from scipy.stats import rankdata
    z = np.load(T6 / "cells.npz")
    idx, cls = z["idx"], z["cls"]
    deps = {"sfc": "magtsurface", "d1m": "magt1m", "d2m": "magt2m"}
    first_ok = 2024  # GIPL 2021-2023 (= 2001-2003) is the start-up period

    def col_of(cell):
        k = np.clip(np.searchsorted(idx, cell), 0, idx.size - 1)
        return np.where(idx[k] == cell, k, -1)

    rows = []
    sites = pd.read_csv(T6 / "borehole_sites.csv")
    b = pd.read_csv(T6 / "borehole_compare_years.csv").merge(sites[["site", "cell"]], on="site")
    b["colk"] = col_of(b.cell.values)
    b = b[(b.colk >= 0) & b.gipl_class.isin([1, 2])]
    cu = pd.read_csv(T6 / "cusp_compare.csv")
    cu = cu[cu.gipl_class.isin([1, 2])].copy()
    for scen in SCENS:
        off = OFFSET[("5ModelAvg", scen)]
        for k, dep in deps.items():
            st = np.load(T6 / f"gipl_5ModelAvg_{scen}_{dep}.npy", mmap_mode="r")
            d = b[b.depth == k].copy()
            d["gipl_matched"] = [np.nanmean(np.asarray(st[[hy + off - 2021, hy + off + 1 - 2021], c], "float32"))
                                 for hy, c in zip(d.hy, d.colk)]
            m = d.groupby("site")[["obs", "esa", "gipl_matched", "gipl_implied"]].mean().dropna()
            rows.append(dict(check="boreholes", scen=scen, depth=k, n=len(m),
                             esa_error=np.median(m.esa - m.obs), gipl_old_implied_error=np.median(m.gipl_implied - m.obs),
                             gipl_matched_error=np.median(m.gipl_matched - m.obs),
                             gipl_matched_mae=np.mean(np.abs(m.gipl_matched - m.obs))))
            vals = []
            for y, c in zip(cu.year_median, cu.colk):
                ys = [g for g in range(y - 2 + off, y + 3 + off) if g >= first_ok]
                vals.append(np.nanmean(np.asarray(st[np.array(ys) - 2021, c], "float32")) if ys else np.nan)
            cu[f"gipl_matched_{k}_{scen}"] = vals
    for scen in SCENS:
        for k in deps:
            for p, label in [(f"esa_{k}", "ESA"), (f"gipl_implied_{k}", "GIPL old implied"),
                             (f"gipl_matched_{k}_{scen}", "GIPL matched years")]:
                d = cu[cu[[f"esa_{k}", f"gipl_implied_{k}", f"gipl_matched_{k}_{scen}"]].notna().all(axis=1)]
                t, yv = d[p].values, d.pf_obs.values
                thr = np.arange(-6, 4.01, 0.1)
                bacc = [0.5 * (np.mean(t[yv == 1] <= th) + np.mean(t[yv == 0] > th)) for th in thr]
                r = rankdata(-t)
                n1, n0 = (yv == 1).sum(), (yv == 0).sum()
                rows.append(dict(check="CUSP", scen=scen, depth=k, predictor=label, n=len(d),
                                 auc=(r[yv == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0),
                                 miss_rate_0C=np.mean(t[yv == 1] > 0), false_frozen_0C=np.mean(t[yv == 0] <= 0),
                                 best_threshold=thr[int(np.argmax(bacc))], best_bal_acc=max(bacc)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "sites20.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(t.round(2).to_string(index=False), flush=True)


def wrf():
    """Independent check with SNAP's WRF-downscaled GFDL-CM3 / NCAR-CCSM4 (RCP 8.5, ~20 km): annual (thawing index -
    freezing index) as an air temperature proxy, matched against GIPL surface 2036-2095 over shifts -5..30."""
    import pandas as pd
    from pyproj import Transformer
    zw = "/vsizip/" + str(SNAP / "AK_WRF/Arctic_EDS_degree_days")
    z, dom, sub = cells()
    yrs = np.arange(2006, 2101)
    with rasterio.open(f"{zw}/thawing_index.zip/thawing_index_NCAR-CCSM4_2050.tif") as s:
        xx, yy = Transformer.from_crs(C.CRS, s.crs, always_xy=True).transform(z["x"][sub], z["y"][sub])
        i, j = lookup(s.transform, s.shape, np.asarray(xx), np.asarray(yy))
    ok = i >= 0

    def proxy(model):
        out = np.full((yrs.size, sub.size), np.nan, "float32")
        for k, yr in enumerate(yrs):
            v = {}
            for ix in ["thawing_index", "freezing_index"]:
                with rasterio.open(f"{zw}/{ix}.zip/{ix}_{model}_{yr}.tif") as s:
                    a = s.read(1).astype("float32")
                    a[a == s.nodata] = np.nan
                v[ix] = np.where(ok, a[i.clip(0), j.clip(0)], np.nan)
            out[k] = v["thawing_index"] - np.abs(v["freezing_index"])
        return out

    w = {m: proxy(m) for m in ["NCAR-CCSM4", "GFDL-CM3"]}
    rows = []
    y0, y1 = 2036, 2095
    for run in RUNS[1:]:
        for scen in SCENS:
            g = gipl(run, scen, "magtsurface", sub, y0, y1)
            for m, a in w.items():
                for off in range(-5, 31):
                    s0 = y0 - off - yrs[0]
                    if 0 <= s0 and s0 + y1 - y0 < yrs.size:
                        rows.append(dict(run=run, scen=scen, wrf_model=m, offset=off,
                                         median_r=np.nanmedian(dcorr(g, a[s0:s0 + y1 - y0 + 1]))))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "wrf.csv", index=False)
    best = t.loc[t.groupby(["run", "scen", "wrf_model"]).median_r.idxmax()]
    print(best.round(2).to_string(index=False), flush=True)


STAGES = {"mask": mask, "pairs": pairs, "highpass": highpass, "yty": yty, "lagscan": lagscan, "season": season,
          "levels": levels, "yearmap": yearmap, "bias20": bias20, "offsets": offsets, "reinterp": reinterp,
          "sites20": sites20, "wrf": wrf}

if __name__ == "__main__":
    if sys.argv[1] == "prep":
        keys = list(SRC)
        prep(keys[int(sys.argv[2])] if sys.argv[2].isdigit() else sys.argv[2])
    elif sys.argv[1] == "list":
        print("\n".join(f"{k}: {i}" for k, i in zip(SRC, range(len(SRC)))))
    else:
        for st_ in (list(STAGES) if sys.argv[1] == "analyze" else sys.argv[1:]):
            STAGES[st_]()
