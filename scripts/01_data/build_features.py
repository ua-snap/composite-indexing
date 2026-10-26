"""Phase A: statewide feature cube on the GIPL 1 km grid (1941 x 2471, EPSG:3338) for T1 (Spearman) and T2 (PCA).

State (historical):
  pfr_2020, pfr_2023 (ESA CCI PFR, %), esa_gst_hist / esa_t1m_hist / esa_alt_hist (2000-2020 means),
  esa_gst_recent (2014-2023 mean, for the T3 splice), maat_hist (CRU TS 4.08, 2000-2020),
  TII: tii_mean, tii_std, thaw_mean, sun_share, shade_share, water_frac (aggregate_tii.py),
  NLCD 2016 class-group fractions: lc_forest, lc_shrub, lc_herb_moss, lc_wetland, lc_barren_other, lc_water.
Projected (5ModelAvg / 5modelAvg; per RCP 4.5 / 8.5 and period base 2014-2023, 2026-2050, 2051-2080, 2081-2100):
  maat_<rcp>_<period>, gipl_sfc_<rcp>_<period> (GIPL magtsurface, MASKED to class 2, D17), and changes vs the base
  dmaat_<rcp>_<period>, dgipl_sfc_<rcp>_<period>. Periods are CLIMATE years: GIPL is read from the files labelled
  20 years later (GIPL_ISSUE_3.md; base 2014-2023 = GIPL files 2034-2043, the same decade as ESA's esa_gst_recent).
Masks: pfr_pos (ESA PFR 2023 > 0; the index gate, D12), gipl_class (statewide_frozen_class.tif).
ESA is sampled at cell centres (nearest 0.01 deg pixel); MAAT = 2 km parent cell.
Output: <data>/features/features_1km.nc
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_tests"))

import numpy as np
import rasterio
import xarray as xr
from pyproj import Transformer

from composite_indexing import config as C
from t1_maat_vs_magt import cell_centres, maat_mean, to_gipl

OUT = C.DATA / "features"
ESA_DIRS = [C.ESA_AK, C.DATA / "esa/alaska_2021_2023"]
SCENS = ["rcp45", "rcp85"]
PERIODS = {"base": (2014, 2023), "2026_2050": (2026, 2050), "2051_2080": (2051, 2080), "2081_2100": (2081, 2100)}
CHANGE_PERIODS = ["2026_2050", "2051_2080", "2081_2100"]  # periods that do not overlap the base
LC_GROUPS = {"lc_forest": [41, 42, 43], "lc_shrub": [51, 52], "lc_herb_moss": [71, 72, 74], "lc_wetland": [90, 95],
             "lc_barren_other": [12, 21, 22, 23, 24, 31, 81, 82], "lc_water": [11]}


class ESASampler:
    """Nearest 0.01 deg ESA pixel at every GIPL cell centre (the ESA Alaska grid is identical across years)."""

    def __init__(self, X, Y):
        f = next((C.ESA_AK / "permafrost_pfr").glob("*-2020-fv05.0.nc"))
        with xr.open_dataset(f) as ds:
            la, lo = ds.lat.values.astype(float), ds.lon.values.astype(float)
        lon, lat = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True).transform(X, Y)
        self.i = np.rint((lat - la[0]) / (la[1] - la[0])).astype(int)
        self.j = np.rint((lon - lo[0]) / (lo[1] - lo[0])).astype(int)
        self.ok = (self.i >= 0) & (self.i < la.size) & (self.j >= 0) & (self.j < lo.size)

    def file(self, sub, year):
        for d in ESA_DIRS:
            hits = sorted((d / sub).glob(f"*-{year}-fv05.0.nc"))
            if hits:
                return hits[0]
        raise FileNotFoundError(f"{sub} {year}")

    def sample(self, sub, var, year):
        with xr.open_dataset(self.file(sub, year)) as ds:  # decoded: fill -> NaN, scale/offset applied
            a = ds[var].values[0]
        out = np.full(self.ok.shape, np.nan, "float32")
        out[self.ok] = a[self.i[self.ok], self.j[self.ok]]
        return out

    def mean(self, sub, var, y0, y1):
        return np.nanmean([self.sample(sub, var, y) for y in range(y0, y1 + 1)], axis=0).astype("float32")


def gipl_sfc_mean(scen, y0, y1):
    """Mean GIPL surface temperature over CLIMATE years y0-y1 (files labelled 20 years later)."""
    acc = 0.0
    for y in range(y0, y1 + 1):
        fy = C.gipl_file_year(y, "5ModelAvg", scen)
        with rasterio.open(C.DATA / f"gipl_tif/magtsurface/gipl_5ModelAvg_{scen}_magtsurface_degC_{fy}.tif") as s:
            a = s.read(1).astype("float32")
        a[a < -9000] = np.nan
        acc = acc + a
    return acc / (y1 - y0 + 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    X, Y = cell_centres(prof)
    good = cls == 2
    v = {}
    esa = ESASampler(X, Y)
    v["pfr_2020"] = esa.sample("permafrost_pfr", "PFR", 2020)
    v["pfr_2023"] = esa.sample("permafrost_pfr", "PFR", 2023)
    v["esa_gst_hist"] = esa.mean("permafrost_gt", "GST", 2000, 2020)
    v["esa_t1m_hist"] = esa.mean("permafrost_gt", "T1m", 2000, 2020)
    v["esa_alt_hist"] = esa.mean("permafrost_alt", "ALT", 2000, 2020)
    v["esa_gst_recent"] = esa.mean("permafrost_gt", "GST", 2014, 2023)
    print("ESA done", flush=True)
    v["maat_hist"] = to_gipl(maat_mean("cru", 2000, 2020), X, Y)
    print("CRU done", flush=True)

    t = np.load(C.DATA / "tii/tii_1km.npz")
    for k in ["tii_mean", "tii_std", "thaw_mean", "sun_share", "shade_share", "water_frac"]:
        v[k] = t[k]
    z = np.load(C.DATA / "landcover/agg/nlcd2016_counts.npz")
    counts, codes = z["counts"].astype("float32"), list(z["codes"])
    tot = counts[..., :-1].sum(-1)
    cov = tot >= 0.9 * 1600
    for g, cl in LC_GROUPS.items():
        idx = [codes.index(c) for c in cl if c in codes]
        v[g] = np.where(cov, counts[..., idx].sum(-1) / np.maximum(tot, 1), np.nan).astype("float32")
    print("TII + NLCD done", flush=True)

    for scen in SCENS:
        m = {p: to_gipl(maat_mean(scen, *yy), X, Y) for p, yy in PERIODS.items()}
        g = {p: np.where(good, gipl_sfc_mean(scen, *yy), np.nan).astype("float32") for p, yy in PERIODS.items()}
        for p in PERIODS:
            v[f"maat_{scen}_{p}"] = m[p]
            v[f"gipl_sfc_{scen}_{p}"] = g[p]
            if p in CHANGE_PERIODS:
                v[f"dmaat_{scen}_{p}"] = m[p] - m["base"]
                v[f"dgipl_sfc_{scen}_{p}"] = g[p] - g["base"]
        print(scen, "done", flush=True)

    tr = prof["transform"]
    x = tr.c + (np.arange(prof["width"]) + 0.5) * tr.a
    y = tr.f + (np.arange(prof["height"]) + 0.5) * tr.e
    ds = xr.Dataset({k: (("y", "x"), np.asarray(a, "float32")) for k, a in v.items()}, coords=dict(x=x, y=y))
    ds["gipl_class"] = (("y", "x"), cls)
    ds["pfr_pos"] = (("y", "x"), (v["pfr_2023"] > 0).astype("uint8"))
    ds.attrs.update(crs=C.CRS, grid="GIPL 2.0 1 km (SNAP)", source="composite-indexing build_features.py",
                    note="gipl_* masked to gipl_class == 2 (D17); periods are climate years (GIPL files + 20, "
                         "GIPL_ISSUE_3.md); changes vs base = 2014-2023")
    enc = {k: {"zlib": True, "complevel": 4} for k in ds.data_vars}
    ds.to_netcdf(OUT / "features_1km.nc", encoding=enc)
    dom = (ds.pfr_pos.values == 1)
    print(f"saved; cells: GIPL valid {int((cls > 0).sum())}, PFR>0 (2023) {int(dom.sum())}, "
          f"PFR>0 & GIPL good {int((dom & good).sum())}")
    for k in ds.data_vars:
        a = ds[k].values[dom].astype(float)
        print(f"  {k:28s} n={np.isfinite(a).sum():7d}  p1/50/99 = {np.nanpercentile(a, [1, 50, 99]).round(2)}")


if __name__ == "__main__":
    main()
