"""Statewide extent of the GIPL frozen-1 m artefact (local source GeoTIFFs only).

Per run (3 models x 2 scenarios): magt1m range over 2021-2120 (streamed min/max); frozen = range < 0.1 degC.
Also 5ModelAvg RCP 8.5 surface year-to-year std, a 2 km border around frozen cells, and the share of the
ESA PFR > 0 domain (2020, sampled at cell centres) that is affected.
Outputs: <data>/results/gipl_artifact/statewide_*.tif + statewide_counts.csv; docs/figures/t3c_statewide_map.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap
from pyproj import Transformer
from scipy import ndimage

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TIF = C.DATA / "gipl_tif"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
YEARS = range(2021, 2121)
MODELS, SCENS = ["5ModelAvg", "GFDL-CM3", "NCAR-CCSM4"], ["rcp45", "rcp85"]
FROZEN = 0.1  # degC
BORDER_KM = 2


def path(var, model, scen, year):
    unit = "degC" if var.startswith("magt") else "m"
    return TIF / var / f"gipl_{model}_{scen}_{var}_{unit}_{year}.tif"


def read(p):
    with rasterio.open(p) as s:
        return s.read(1, masked=True).astype("float32").filled(np.nan), s.profile


def magt1m_range(model, scen):
    lo = hi = None
    for y in YEARS:
        a, prof = read(path("magt1m", model, scen, y))
        lo = a if lo is None else np.fmin(lo, a)
        hi = a if hi is None else np.fmax(hi, a)
    return hi - lo, prof


def surface_iav(model="5ModelAvg", scen="rcp85"):
    prev, n, s1, s2 = None, 0, 0.0, 0.0
    for y in YEARS:
        a, _ = read(path("magtsurface", model, scen, y))
        if prev is not None:
            d = a - prev
            s1, s2, n = s1 + d, s2 + d * d, n + 1
        prev = a
    return np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0))


def esa_pfr_on_grid(prof):
    """ESA PFR 2020 (nearest 0.01 deg pixel) at each GIPL cell centre."""
    f = next((C.ESA_AK / "permafrost_pfr").glob("*-2020-fv05.0.nc"))
    ds = xr.open_dataset(f)
    la, lo = ds.lat.values.astype(float), ds.lon.values.astype(float)
    pfr = ds.PFR.values[0]
    h, w, t = prof["height"], prof["width"], prof["transform"]
    xs = t.c + (np.arange(w) + 0.5) * t.a
    ys = t.f + (np.arange(h) + 0.5) * t.e
    X, Y = np.meshgrid(xs, ys)
    lon, lat = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True).transform(X, Y)
    i = np.rint((lat - la[0]) / (la[1] - la[0])).astype(int)
    j = np.rint((lon - lo[0]) / (lo[1] - lo[0])).astype(int)
    ok = (i >= 0) & (i < la.size) & (j >= 0) & (j < lo.size)
    out = np.full(X.shape, np.nan, "float32")
    out[ok] = pfr[i[ok], j[ok]]
    return out


def write(name, a, prof, dtype="float32", nodata=np.nan):
    p = dict(prof, dtype=dtype, nodata=nodata, compress="lzw", tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(OUT / f"statewide_{name}.tif", "w", **p) as d:
        d.write(a.astype(dtype), 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen, rows = {}, []
    for model in MODELS:
        for scen in SCENS:
            r, prof = magt1m_range(model, scen)
            frozen[(model, scen)] = r < FROZEN
            if (model, scen) == ("5ModelAvg", "rcp85"):
                write("magt1m_range_5ModelAvg_rcp85", r, prof)
                valid = np.isfinite(r)
            print(f"{model} {scen}: frozen {frozen[(model, scen)].sum()}", flush=True)
    ref = frozen[("5ModelAvg", "rcp85")]
    any_ = np.logical_or.reduce(list(frozen.values()))
    all_ = np.logical_and.reduce(list(frozen.values()))
    border = ndimage.binary_dilation(any_, iterations=BORDER_KM) & ~any_ & valid
    iav = surface_iav()
    write("surface_iav_5ModelAvg_rcp85", iav, prof)
    pfr = esa_pfr_on_grid(prof)
    pf = valid & (pfr > 0) & (pfr <= 100)
    cls = np.zeros(ref.shape, "uint8")  # 0 nodata, 1 valid no PF, 2 valid ESA PFR > 0, 3 border, 4 frozen (any run)
    cls[valid], cls[pf], cls[border], cls[any_] = 1, 2, 3, 4
    write("frozen_class", cls, prof, dtype="uint8", nodata=0)
    n_valid, n_pf = int(valid.sum()), int(pf.sum())
    for (model, scen), f in frozen.items():
        rows.append(dict(run=f"{model} {scen}", frozen=int(f.sum()), share_valid=f.sum() / n_valid,
                         share_pfr_domain=(f & pf).sum() / n_pf, overlap_with_5ModelAvg_rcp85=int((f & ref).sum())))
    for name, m in [("frozen in ANY run", any_), ("frozen in ALL runs", all_), (f"{BORDER_KM} km border", border)]:
        rows.append(dict(run=name, frozen=int(m.sum()), share_valid=m.sum() / n_valid,
                         share_pfr_domain=(m & pf).sum() / n_pf))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "statewide_counts.csv", index=False)
    print(f"valid GIPL cells {n_valid}; ESA PFR>0 domain {n_pf}")
    print(df.round(4).to_string(index=False))
    print("frozen (any run) ESA PFR 2020 quantiles:", np.nanpercentile(pfr[any_], [10, 50, 90]).round(1),
          "| PFR>0 domain:", np.nanpercentile(pfr[pf], [10, 50, 90]).round(1))
    lab, n = ndimage.label(any_)
    sizes = np.bincount(lab.ravel())[1:]
    print(f"patches: {n}; size km2 median {np.median(sizes):.0f}, p90 {np.percentile(sizes, 90):.0f}, "
          f"max {sizes.max()}; share of frozen area in patches >= 25 km2: {sizes[sizes >= 25].sum() / sizes.sum():.2f}")
    for k in np.argsort(np.bincount(lab.ravel())[1:])[::-1][:8] + 1:
        r, c = ndimage.center_of_mass(lab == k)
        lon, lat = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True).transform(*(prof["transform"] * (c + 0.5, r + 0.5)))
        print(f"  patch {(lab == k).sum():6d} km2, centre {lat:.2f}N {-lon:.2f}W")
    print("frozen magt1m value (5ModelAvg rcp85, year 2021) quantiles:",
          np.nanpercentile(read(path('magt1m', '5ModelAvg', 'rcp85', 2021))[0][ref], [1, 10, 50, 90, 99]).round(2))

    # --- map
    t = prof["transform"]
    ext = (t.c, t.c + prof["width"] * t.a, t.f + prof["height"] * t.e, t.f)
    cmap = ListedColormap(["#ffffff", "#f0efec", "#cfcdc6", "#f6b79d", "#c2410c"])
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.imshow(cls, extent=ext, cmap=cmap, vmin=-0.5, vmax=4.5, interpolation="nearest")
    for key, label, lon, lat in C.REGIONS:
        x, y = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True).transform(lon, lat)
        ax.plot(x, y, "s", mfc="none", mec="#0b0b0b", ms=8, mew=1.2)
        ax.annotate(label, (x, y), xytext=(6, 6), textcoords="offset points", fontsize=9, color="#0b0b0b")
    any_row = df[df.run == "frozen in ANY run"].iloc[0]
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in ["#c2410c", "#f6b79d", "#cfcdc6", "#f0efec"]]
    ax.legend(handles, [f"GIPL 1 m frozen in any run ({any_row.frozen:,} km², {any_row.share_pfr_domain:.1%} of PFR > 0)",
                        f"{BORDER_KM} km border", "other cells, ESA PFR > 0 (2020)", "other cells, ESA PFR = 0"],
              loc="lower left", frameon=False, fontsize=9)
    ax.set_title("Where GIPL 2.0 1 m ground temperature never changes (2021–2120, < 0.1 °C)", loc="left",
                 fontsize=12, color="#0b0b0b")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    fig.savefig(FIG / "t3c_statewide_map.png", dpi=170, bbox_inches="tight")


if __name__ == "__main__":
    main()
