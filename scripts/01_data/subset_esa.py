"""ESA CCI Permafrost v5.0 at the pilot GIPL 1 km cells, 2000-2023 (local files only; read-only sources).

Each 1 km cell value = area-weighted mean of the 0.01 deg ESA pixels covering it (10 x 10 sub-samples per cell,
nearest pixel each). 2000-2020 from the Alaska subsets, 2021-2023 from the raw NH files (same 0.01 deg grid).
Output: <data>/esa/esa_pilot_cells.nc, dims (cell, year); cell order = windows/gipl_cells.csv rows.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

from composite_indexing import config as C

YEARS = range(2000, 2024)
SUB = 10  # sub-samples per cell side
# product: (Alaska subset dir, raw NH dir, file tag, variables)
PRODUCTS = {
    "pfr": ("permafrost_pfr", "permafrost_extent", "PFR", ["PFR"]),
    "gt": ("permafrost_gt", "ground_temperature", "GTD", ["GST", "T1m", "T2m", "T5m"]),
    "alt": ("permafrost_alt", "active_layer_thickness", "ALT", ["ALT"]),
}
TO_LL = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True)


def find(product, year):
    ak, raw, tag, _ = PRODUCTS[product]
    pat = f"ESACCI-PERMAFROST-L4-{tag}-*-{year}-fv05.0.nc"
    hits = sorted((C.ESA_AK / ak).glob(pat)) or sorted(
        (C.ESA_RAW / f"data/{raw}/L4/area4/pp/v05.0/northern_hemisphere/{year}").glob(pat))
    if not hits:
        raise FileNotFoundError(f"{product} {year}")
    return hits[0]


def subsample_ll(cells):
    """lon/lat of SUB x SUB sub-points per 1 km cell: arrays (ncell, SUB*SUB)."""
    off = (np.arange(SUB) + 0.5) / SUB * C.GIPL_RES - C.GIPL_RES / 2
    dx, dy = [a.ravel() for a in np.meshgrid(off, off)]
    x = cells.x.values[:, None] + dx[None]
    y = cells.y.values[:, None] + dy[None]
    lon, lat = TO_LL.transform(x, y)
    return lon, lat


def sample(path, variables, lon, lat):
    """Cell means of each variable; reads only the bounding box of the sub-points."""
    ds = xr.open_dataset(path)  # mask_and_scale: float, NaN fill
    la, lo = ds.lat.values.astype(float), ds.lon.values.astype(float)
    i = np.rint((lat - la[0]) / (la[1] - la[0])).astype(int)
    j = np.rint((lon - lo[0]) / (lo[1] - lo[0])).astype(int)
    i0, i1, j0, j1 = i.min(), i.max() + 1, j.min(), j.max() + 1
    out = {}
    for v in variables:
        a = ds[v].isel(time=0, lat=slice(i0, i1), lon=slice(j0, j1)).values.astype(float)
        out[v] = np.nanmean(a[i - i0, j - j0], axis=1)  # NaN only if all sub-points are fill
    return out


def main():
    cells = pd.read_csv(C.DATA / "windows/gipl_cells.csv")
    lon, lat = subsample_ll(cells)
    data, src = {}, {}
    for product, (*_, variables) in PRODUCTS.items():
        for v in variables:
            data[v] = np.full((len(cells), len(YEARS)), np.nan)
        for k, year in enumerate(YEARS):
            path = find(product, year)
            src[(product, year)] = path.name
            for region in cells.region.unique():
                m = (cells.region == region).values
                for v, vals in sample(path, variables, lon[m], lat[m]).items():
                    data[v][m, k] = vals
        print(f"{product}: done ({', '.join(variables)})")
    ds = xr.Dataset(
        {v: (("cell", "year"), a) for v, a in data.items()},
        coords=dict(cell=np.arange(len(cells)), year=list(YEARS), region=("cell", cells.region.to_numpy(dtype=str)),
                    x=("cell", cells.x.values), y=("cell", cells.y.values)),
        attrs=dict(source="ESA CCI Permafrost v5.0 L4 area4 PP; 1 km cell = mean of 10x10 sub-sampled 0.01 deg pixels",
                   note="2000-2002 ERA5_MODISLST_BIASCORRECTED, 2003+ MODISLST_CRYOGRID; 2021-2023 from raw NH files"),
    )
    for v in ["GST", "T1m", "T2m", "T5m"]:
        ds[v].attrs["units"] = "degC"
    ds["PFR"].attrs["units"] = "percent"
    ds["ALT"].attrs["units"] = "m"
    out = C.DATA / "esa/esa_pilot_cells.nc"
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)
    print(out, dict(ds.sizes))
    print(ds.to_dataframe().groupby("region")[["PFR", "GST", "T1m", "ALT"]].median().round(2))


if __name__ == "__main__":
    main()
