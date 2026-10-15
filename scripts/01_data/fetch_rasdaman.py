"""Fetch Rasdaman (Zeus) subsets for the pilot windows. Cached; sequential; polite (see rasdaman.py).

Modes:
  smoke  - ONE tiny request per `_wcs` coverage (3 x 3 cells at the Fairbanks window centre; GIPL one slice,
           tas one year x 12 months), then 2 labelled API point calls to spot-check the axis encodings.
  verify - 1 cell x full series: tas proj GFDL-CM3 rcp45 (year offset) and GIPL all models/scenarios (indices).
  pilot  - one request per window per coverage (9): GIPL 4 fields, tas hist, tas proj; full model/scenario/time.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import xarray as xr
from pyproj import Transformer

from composite_indexing import api
from composite_indexing import config as C
from composite_indexing.rasdaman import get_coverage

TO_LL = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True)
GIPL, TAS_H, TAS_P = "crrel_gipl_outputs_nc_wcs", "tas_2km_historical_wcs", "tas_2km_projected_wcs"
EPS = 1.0  # m inside the cell edges, so a subset never touches a neighbouring cell


def windows():
    return {w["region"]: w for w in json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]}


def block(xc, yc, x0, y0, res, n=3):
    """Edges of the n x n block of grid cells centred on the cell containing (xc, yc)."""
    i, j = np.floor((xc - x0) / res), np.floor((yc - y0) / res)
    h = (n - 1) // 2
    bx0, by0 = x0 + (i - h) * res, y0 + (j - h) * res
    centre = (x0 + (i + 0.5) * res, y0 + (j + 0.5) * res)
    return (bx0 + EPS, bx0 + n * res - EPS), (by0 + EPS, by0 + n * res - EPS), centre


def show(path):
    ds = xr.open_dataset(path)
    print(f"  {path.name} ({path.stat().st_size} B)")
    print("  " + str(ds).replace("\n", "\n  "))
    return ds


def smoke():
    w = windows()["fairbanks"]
    xc, yc = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
    gx, gy, gcen = block(xc, yc, C.GIPL_X0, C.GIPL_Y0, C.GIPL_RES)
    tx, ty, tcen = block(xc, yc, C.TAS_X0, C.TAS_Y0, C.TAS_RES)

    print("GIPL: 5ModelAvg, RCP 4.5, 2021, magt1m")
    g = show(get_coverage(GIPL, [("model", 0), ("scenario", 0), ("time", "2021-01-01T00:00:00.000Z"),
                                 ("X", *gx), ("Y", *gy)], ["magt1m_degC"], label="smoke_fbk"))
    print("tas historical: 2015 (index 114), 12 months")
    h = show(get_coverage(TAS_H, [("year", 114), ("X", *tx), ("Y", *ty)], ["tas"], label="smoke_fbk"))
    print("tas projected: 5ModelAvg, rcp45, 2006 (index 0), 12 months")
    p = show(get_coverage(TAS_P, [("model", 0), ("scenario", 0), ("year", 0), ("X", *tx), ("Y", *ty)], ["tas"],
                          label="smoke_fbk"))

    # labelled API at the centre cells
    glon, glat = TO_LL.transform(*gcen)
    tlon, tlat = TO_LL.transform(*tcen)
    print(f"\nGIPL centre cell {gcen} -> {glat:.4f}, {glon:.4f}; tas centre cell {tcen} -> {tlat:.4f}, {tlon:.4f}")
    a_g = api.get_json(f"/permafrost/point/gipl/{glat:.4f}/{glon:.4f}", label="smoke_gipl")
    a_t = api.get_json(f"/temperature/{tlat:.4f}/{tlon:.4f}", label="smoke_temperature")
    return dict(g=g, h=h, p=p, a_g=a_g, a_t=a_t, gcen=gcen, tcen=tcen)


def one_cell(cx, cy, res):
    return (cx - res / 2 + EPS, cx + res / 2 - EPS), (cy - res / 2 + EPS, cy + res / 2 - EPS)


def verify():
    """Full series at the smoke centre cells: tas proj GFDL-CM3 rcp45 (year offset); GIPL all models/scenarios."""
    w = windows()["fairbanks"]
    xc, yc = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
    *_, gcen = block(xc, yc, C.GIPL_X0, C.GIPL_Y0, C.GIPL_RES)
    *_, tcen = block(xc, yc, C.TAS_X0, C.TAS_Y0, C.TAS_RES)
    tx, ty = one_cell(*tcen, C.TAS_RES)
    gx, gy = one_cell(*gcen, C.GIPL_RES)
    p = show(get_coverage(TAS_P, [("model", 1), ("scenario", 0), ("X", *tx), ("Y", *ty)], ["tas"],
                          label="verify_fbk_gfdl45"))
    g = show(get_coverage(GIPL, [("X", *gx), ("Y", *gy)], ["magt1m_degC"], label="verify_fbk_cell"))
    return p, g


GIPL_FIELDS = ["magt1m_degC", "magtsurface_degC", "permafrosttop_m", "talikthickness_m"]


def pilot():
    """One request per window per coverage (9 total): full model/scenario/time axes over the window."""
    import pandas as pd
    tas = pd.read_csv(C.DATA / "windows/tas_cells.csv")
    for key, w in windows().items():
        gx, gy = (w["x0"] + EPS, w["x1"] - EPS), (w["y0"] + EPS, w["y1"] - EPS)
        t = tas[tas.region == key]
        tx = (C.TAS_X0 + t.ix.min() * C.TAS_RES + EPS, C.TAS_X0 + (t.ix.max() + 1) * C.TAS_RES - EPS)
        ty = (C.TAS_Y0 + t.iy.min() * C.TAS_RES + EPS, C.TAS_Y0 + (t.iy.max() + 1) * C.TAS_RES - EPS)
        for cov, sub, fields in [(GIPL, [("X", *gx), ("Y", *gy)], GIPL_FIELDS),
                                 (TAS_H, [("X", *tx), ("Y", *ty)], ["tas"]),
                                 (TAS_P, [("X", *tx), ("Y", *ty)], ["tas"])]:
            path = get_coverage(cov, sub, fields, label=f"pilot_{key}")
            ds = xr.open_dataset(path)
            print(f"{key:10s} {cov:28s} {path.stat().st_size / 1e6:6.2f} MB  {dict(ds.sizes)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "verify", "pilot"])
    {"smoke": smoke, "verify": verify, "pilot": pilot}[ap.parse_args().mode]()
