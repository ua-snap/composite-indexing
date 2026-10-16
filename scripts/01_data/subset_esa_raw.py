"""Cut 2021-2023 ESA CCI Permafrost v5.0 (PFR, GTD, ALT) from the raw northern-hemisphere files (READ-ONLY) to the
same Alaska box and file layout as the existing 2000-2020 subsets (D12), so 2000-2023 can be read as one series.

Box: lat 50-72.5 N, lon 180-125 W on the native 0.01 deg grid (same 2250 x 5500 pixels as the existing subsets).
Values are copied raw (no decoding), with the original encoding attributes.
Output: <data>/esa/alaska_2021_2023/{permafrost_pfr,permafrost_gt,permafrost_alt}/<original file name>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import xarray as xr

from composite_indexing import config as C

YEARS = [2021, 2022, 2023]
PRODUCTS = {"permafrost_pfr": ("permafrost_extent", "PFR"), "permafrost_gt": ("ground_temperature", "GTD"),
            "permafrost_alt": ("active_layer_thickness", "ALT")}
OUT = C.DATA / "esa/alaska_2021_2023"


def reference_grid():
    f = next((C.ESA_AK / "permafrost_pfr").glob("*-2020-fv05.0.nc"))
    with xr.open_dataset(f) as ds:
        return ds.lat.values.astype(float), ds.lon.values.astype(float)


def main():
    lat_ref, lon_ref = reference_grid()
    for sub, (raw, tag) in PRODUCTS.items():
        (OUT / sub).mkdir(parents=True, exist_ok=True)
        for y in YEARS:
            src = next((C.ESA_RAW / f"data/{raw}/L4/area4/pp/v05.0/northern_hemisphere/{y}").glob(
                f"ESACCI-PERMAFROST-L4-{tag}-*-{y}-fv05.0.nc"))
            dst = OUT / sub / src.name
            if dst.exists():
                print("exists", dst.name)
                continue
            ds = xr.open_dataset(src, mask_and_scale=False, decode_times=False)
            la, lo = ds.lat.values.astype(float), ds.lon.values.astype(float)
            i0 = int(np.argmin(np.abs(la - lat_ref[0])))
            j0 = int(np.argmin(np.abs(lo - lon_ref[0])))
            sub_ds = ds.isel(lat=slice(i0, i0 + lat_ref.size), lon=slice(j0, j0 + lon_ref.size)).load()
            assert np.allclose(sub_ds.lat.values, lat_ref, atol=1e-4) and np.allclose(sub_ds.lon.values, lon_ref,
                                                                                      atol=1e-4)
            enc = {}
            for v in sub_ds.data_vars:
                fv = sub_ds[v].attrs.pop("_FillValue", None)
                e = {"zlib": True, "complevel": 4}
                if sub_ds[v].ndim == 3:
                    e["chunksizes"] = (1, 1125, 2750)
                if fv is not None:
                    e["_FillValue"] = fv
                enc[v] = e
            sub_ds.attrs["subset"] = (f"Alaska bbox {{'west': -180.0, 'south': 50.0, 'east': -125.0, 'north': 72.5}} "
                                      f"clipped from {src.name} on native grid (composite-indexing subset_esa_raw.py)")
            sub_ds.to_netcdf(dst, encoding=enc)
            # verify: identical raw values in a sample window
            chk = xr.open_dataset(dst, mask_and_scale=False, decode_times=False)
            v0 = list(chk.data_vars)[-1]
            a = chk[v0].values[..., 1000:1100, 3000:3100]
            b = ds[v0].isel(lat=slice(i0 + 1000, i0 + 1100), lon=slice(j0 + 3000, j0 + 3100)).values
            print(f"{dst.name}: {dict(chk.sizes)}, check {v0} identical: {np.array_equal(a, b)}", flush=True)


if __name__ == "__main__":
    main()
