"""Choose one 10 x 10 km pilot window inside each 60 km TII sample area (local data only; no server calls).

Candidates are snapped to the GIPL 1 km grid edges and slide in 1 km steps through the 60 km box. Each is scored on
local inputs:
  - ESA CCI PFR (2020) sampled at the 100 GIPL cell centres: share of cells with PFR > 0, and PFR spread;
  - TII (32 m): terrain mix = entropy of the flat / sun-facing / shaded area shares (|TII| <= 0.1 is flat);
  - water fraction (ArcticDEM water mask) and TII coverage.
Hard filters: water < 5 %, TII valid >= 98 %, PFR > 0 in >= 90 % of cells (relaxed if no candidate passes),
terrain mix >= MIN_MIX (dropped if none pass). Choice: largest PFR spread (std over the 100 cells).

Outputs (data dir, windows/): candidates_<region>.csv, pilot_windows.gpkg/.json, gipl_cells.csv, tas_cells.csv,
quicklook_windows.png.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from pyproj import Transformer
from rasterio.windows import from_bounds
from shapely.geometry import box

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = C.DATA / "windows"
FLAT = 0.1  # |TII| <= FLAT counts as flat (same tolerance as the thaw_score offset)
MIN_MIX = 0.75  # minimum terrain mix (normalized entropy of flat / sun / shade shares)
STEP = 1000
N = int(C.WINDOW / C.GIPL_RES)  # cells per window side (10)
TO_3338 = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True)
TO_LL = Transformer.from_crs(C.CRS, "EPSG:4326", always_xy=True)


def snap(v, origin, res):
    """Nearest grid edge to v."""
    return origin + round((v - origin) / res) * res


def load_pfr(year=2020):
    f = next((C.ESA_AK / "permafrost_pfr").glob(f"*-{year}-fv05.0.nc"))
    ds = xr.open_dataset(f, mask_and_scale=False)
    lat, lon = ds.lat.values.astype(float), ds.lon.values.astype(float)
    return ds.PFR.values[0], lat, lon


def sample_pfr(pfr, lat, lon, x, y):
    """Nearest 0.01 deg PFR pixel at EPSG:3338 points; NaN for fill."""
    lo, la = TO_LL.transform(x, y)
    i = np.clip(np.rint((la - lat[0]) / (lat[1] - lat[0])).astype(int), 0, lat.size - 1)
    j = np.clip(np.rint((lo - lon[0]) / (lon[1] - lon[0])).astype(int), 0, lon.size - 1)
    v = pfr[i, j].astype(float)
    v[v == 255] = np.nan
    return v


def read_box(path, x0, y0, x1, y1):
    with rasterio.open(path) as s:
        w = from_bounds(x0, y0, x1, y1, s.transform).round_offsets().round_lengths()
        return s.read(1, window=w), s.window_transform(w)


def entropy3(a, b, c):
    p = np.array([a, b, c])
    p = p[p > 0]
    return float(-(p * np.log(p)).sum() / np.log(3))


def gipl_centres(x0, y0):
    xc = x0 + (np.arange(N) + 0.5) * C.GIPL_RES
    yc = y0 + (np.arange(N) + 0.5) * C.GIPL_RES
    return np.meshgrid(xc, yc[::-1])


def score_region(key, lon, lat, pfr, plat, plon):
    cx, cy = TO_3338.transform(lon, lat)
    bx0, by0 = snap(cx - C.REGION_HALF, C.GIPL_X0, C.GIPL_RES), snap(cy - C.REGION_HALF, C.GIPL_Y0, C.GIPL_RES)
    side = 2 * C.REGION_HALF
    tii, tt = read_box(C.TII_TIF, bx0, by0, bx0 + side, by0 + side)
    wat, wt = read_box(C.WATER_TIF, bx0, by0, bx0 + side, by0 + side)
    px = tt.a  # 32 m
    rows = []
    for ox in range(0, side - C.WINDOW + 1, STEP):
        for oy in range(0, side - C.WINDOW + 1, STEP):
            x0, y0 = bx0 + ox, by0 + oy
            c0, r0 = int(round((x0 - tt.c) / px)), int(round((tt.f - (y0 + C.WINDOW)) / px))
            n = int(round(C.WINDOW / px))
            t = tii[r0:r0 + n, c0:c0 + n]
            wc0, wr0 = int(round((x0 - wt.c) / px)), int(round((wt.f - (y0 + C.WINDOW)) / px))
            w = wat[wr0:wr0 + n, wc0:wc0 + n]
            valid = np.isfinite(t)
            tv = t[valid]
            f_flat, f_sun = np.mean(np.abs(tv) <= FLAT), np.mean(tv > FLAT)
            f_shade = 1 - f_flat - f_sun
            gx, gy = gipl_centres(x0, y0)
            p = sample_pfr(pfr, plat, plon, gx.ravel(), gy.ravel())
            if np.isnan(p).all():  # all fill (e.g. glacier): cannot pass the PFR filter
                p = np.zeros(1)
            rows.append(dict(
                region=key, x0=x0, y0=y0, x1=x0 + C.WINDOW, y1=y0 + C.WINDOW,
                water=float(np.mean(w == 1)), tii_valid=float(valid.mean()),
                tii_std=float(np.std(tv)), f_flat=f_flat, f_sun=f_sun, f_shade=f_shade,
                terrain_mix=entropy3(f_flat, f_sun, f_shade),
                thaw_mean=float(np.mean(np.clip((tv - C.THAW_T0) / (C.THAW_T1 - C.THAW_T0), 0, 1))),
                pfr_pos=float(np.mean(p > 0)), pfr_mean=float(np.nanmean(p)), pfr_std=float(np.nanstd(p)),
                pfr_min=float(np.nanmin(p)), pfr_max=float(np.nanmax(p)),
            ))
    df = pd.DataFrame(rows)
    ok = (df.water < 0.05) & (df.tii_valid >= 0.98)
    for need in (0.9, 0.75, 0.5, 0.0):
        keep = ok & (df.pfr_pos >= need)
        if keep.any():
            break
    df["pass"] = keep
    df["pfr_pos_required"] = need
    # slopes AND flats are a requirement; among those, the most PFR variety wins
    mixed = keep & (df.terrain_mix >= MIN_MIX)
    df["score"] = np.where(mixed if mixed.any() else keep, df.pfr_std, np.nan)
    return df, (bx0, by0, bx0 + side, by0 + side), tii, tt


def cells_tables(win):
    g, t = [], []
    for r in win.itertuples():
        gx, gy = gipl_centres(r.x0, r.y0)
        lo, la = TO_LL.transform(gx.ravel(), gy.ravel())
        ix = np.rint((gx.ravel() - C.GIPL_X0) / C.GIPL_RES - 0.5).astype(int)
        iy = np.rint((gy.ravel() - C.GIPL_Y0) / C.GIPL_RES - 0.5).astype(int)
        g.append(pd.DataFrame(dict(region=r.region, x=gx.ravel(), y=gy.ravel(), lon=lo, lat=la, ix=ix, iy=iy)))
        # every tas 2 km cell that overlaps the window
        i0 = int(np.floor((r.x0 - C.TAS_X0) / C.TAS_RES)); i1 = int(np.ceil((r.x1 - C.TAS_X0) / C.TAS_RES))
        j0 = int(np.floor((r.y0 - C.TAS_Y0) / C.TAS_RES)); j1 = int(np.ceil((r.y1 - C.TAS_Y0) / C.TAS_RES))
        ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1))
        tx = C.TAS_X0 + (ii.ravel() + 0.5) * C.TAS_RES
        ty = C.TAS_Y0 + (jj.ravel() + 0.5) * C.TAS_RES
        lo, la = TO_LL.transform(tx, ty)
        t.append(pd.DataFrame(dict(region=r.region, x=tx, y=ty, lon=lo, lat=la, ix=ii.ravel(), iy=jj.ravel())))
    return pd.concat(g, ignore_index=True), pd.concat(t, ignore_index=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pfr, plat, plon = load_pfr()
    chosen, panels = [], []
    for key, label, lon, lat in C.REGIONS:
        df, rbox, tii, tt = score_region(key, lon, lat, pfr, plat, plon)
        df.to_csv(OUT / f"candidates_{key}.csv", index=False)
        best = df.loc[df.score.idxmax()].copy()
        best["label"] = label
        chosen.append(best)
        panels.append((label, rbox, tii, tt, best, df))
        print(f"{label}: {int(df['pass'].sum())}/{len(df)} candidates pass (PFR>0 share >= {best.pfr_pos_required})")
        print(best[["x0", "y0", "water", "tii_std", "f_flat", "f_sun", "f_shade", "terrain_mix", "pfr_pos",
                    "pfr_mean", "pfr_std", "pfr_min", "pfr_max"]].to_string())

    win = pd.DataFrame(chosen).reset_index(drop=True)
    clon, clat = TO_LL.transform(((win.x0 + win.x1) / 2).values, ((win.y0 + win.y1) / 2).values)
    win["centre_lon"], win["centre_lat"] = clon, clat
    gdf = gpd.GeoDataFrame(win, geometry=[box(r.x0, r.y0, r.x1, r.y1) for r in win.itertuples()], crs=C.CRS)
    gdf.to_file(OUT / "pilot_windows.gpkg", driver="GPKG")
    cols = ["region", "label", "x0", "y0", "x1", "y1", "centre_lon", "centre_lat"]
    (OUT / "pilot_windows.json").write_text(json.dumps(
        {"crs": C.CRS, "windows": win[cols].to_dict(orient="records")}, indent=2, default=float))
    g, t = cells_tables(win)
    g.to_csv(OUT / "gipl_cells.csv", index=False)
    t.to_csv(OUT / "tas_cells.csv", index=False)
    print(f"GIPL cells: {len(g)}; tas cells: {len(t)} ({t.groupby('region').size().to_dict()})")

    # quick look: TII of each 60 km box with the chosen window
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (label, (x0, y0, x1, y1), tii, tt, best, _) in zip(axs, panels):
        ext = (tt.c, tt.c + tii.shape[1] * tt.a, tt.f + tii.shape[0] * tt.e, tt.f)
        im = ax.imshow(tii, extent=ext, cmap="RdBu_r", vmin=-1.2, vmax=1.2)
        ax.add_patch(plt.Rectangle((best.x0, best.y0), C.WINDOW, C.WINDOW, fill=False, ec="k", lw=2))
        ax.set_title(f"{label}: PFR {best.pfr_min:.0f}-{best.pfr_max:.0f}%, mix {best.terrain_mix:.2f}")
        ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axs, shrink=0.8, label="TII (kWh m$^{-2}$ day$^{-1}$)")
    fig.savefig(OUT / "quicklook_windows.png", dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
