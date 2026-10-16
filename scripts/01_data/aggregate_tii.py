"""Terrain insolation index (TII, 32 m, ArcticDEM-PISR; READ-ONLY) summarized per GIPL 1 km cell, statewide.

Each 32 m pixel is assigned to the GIPL cell containing its centre (no resampling). Water pixels (ArcticDEM water
mask = 1) are excluded from the terrain statistics. Per cell:
  tii_mean, tii_std, thaw_mean (thaw_score = clip((TII - 0.1)/(1.4 - 0.1), 0, 1)), sun_share (TII > 0.1),
  shade_share (TII < -0.1), water_frac, n_valid (land pixels with TII).
Output: <data>/tii/tii_1km.npz (arrays on the GIPL grid, 1941 x 2471) + tii_1km_<field>.tif quick-look GeoTIFFs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import Window

from composite_indexing import config as C

OUT = C.DATA / "tii"
STRIP = 512  # TII rows per read (= block height)
FLAT = 0.1
NCELL = C.GIPL_NY * C.GIPL_NX
GIPL_TOP = C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    acc = {k: np.zeros(NCELL, np.float64) for k in ["n", "s", "s2", "thaw", "sun", "shade", "water", "all"]}
    with rasterio.open(C.TII_TIF) as tii, rasterio.open(C.WATER_TIF) as wat:
        assert tii.transform == wat.transform and tii.shape == wat.shape
        t = tii.transform
        xs = t.c + (np.arange(tii.width) + 0.5) * t.a
        gc = np.floor((xs - C.GIPL_X0) / C.GIPL_RES).astype(np.int64)
        col_ok = (gc >= 0) & (gc < C.GIPL_NX)
        for r0 in range(0, tii.height, STRIP):
            nr = min(STRIP, tii.height - r0)
            w = Window(0, r0, tii.width, nr)
            a = tii.read(1, window=w)
            water = wat.read(1, window=w) == 1
            ys = t.f + (np.arange(r0, r0 + nr) + 0.5) * t.e
            gr = np.floor((GIPL_TOP - ys) / C.GIPL_RES).astype(np.int64)
            row_ok = (gr >= 0) & (gr < C.GIPL_NY)
            inside = row_ok[:, None] & col_ok[None, :]
            cell = gr[:, None] * C.GIPL_NX + gc[None, :]
            seen = inside & (np.isfinite(a) | water)
            land = inside & np.isfinite(a) & ~water
            c_all, c_land = cell[seen], cell[land]
            v = a[land].astype(np.float64)
            acc["all"] += np.bincount(c_all, minlength=NCELL)
            acc["water"] += np.bincount(cell[inside & water], minlength=NCELL)
            acc["n"] += np.bincount(c_land, minlength=NCELL)
            acc["s"] += np.bincount(c_land, weights=v, minlength=NCELL)
            acc["s2"] += np.bincount(c_land, weights=v * v, minlength=NCELL)
            acc["thaw"] += np.bincount(c_land, weights=np.clip((v - C.THAW_T0) / (C.THAW_T1 - C.THAW_T0), 0, 1),
                                       minlength=NCELL)
            acc["sun"] += np.bincount(c_land, weights=(v > FLAT).astype(float), minlength=NCELL)
            acc["shade"] += np.bincount(c_land, weights=(v < -FLAT).astype(float), minlength=NCELL)
            if (r0 // STRIP) % 10 == 0:
                print(f"row {r0}/{tii.height}", flush=True)
    n = acc["n"]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = acc["s"] / n
        out = dict(tii_mean=mean, tii_std=np.sqrt(np.maximum(acc["s2"] / n - mean ** 2, 0)), thaw_mean=acc["thaw"] / n,
                   sun_share=acc["sun"] / n, shade_share=acc["shade"] / n, water_frac=acc["water"] / acc["all"])
    shape = (C.GIPL_NY, C.GIPL_NX)
    out = {k: v.reshape(shape).astype(np.float32) for k, v in out.items()}
    out["n_valid"] = n.reshape(shape).astype(np.int32)
    np.savez_compressed(OUT / "tii_1km.npz", **out)
    prof = dict(driver="GTiff", width=C.GIPL_NX, height=C.GIPL_NY, count=1, dtype="float32", crs=C.CRS, nodata=np.nan,
                transform=Affine(C.GIPL_RES, 0, C.GIPL_X0, 0, -C.GIPL_RES, GIPL_TOP), compress="lzw")
    for k in ["tii_mean", "thaw_mean", "sun_share", "water_frac"]:
        with rasterio.open(OUT / f"tii_1km_{k}.tif", "w", **prof) as d:
            d.write(out[k], 1)
    ok = out["n_valid"] > 0
    print(f"cells with TII: {ok.sum()}; median pixels/cell {np.median(out['n_valid'][ok]):.0f} (full cell = 977)")
    for k in ["tii_mean", "tii_std", "thaw_mean", "sun_share", "shade_share", "water_frac"]:
        print(f"  {k}: p1/50/99 = {np.nanpercentile(out[k][ok], [1, 50, 99]).round(3)}")


if __name__ == "__main__":
    main()
