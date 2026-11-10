"""Summarize SNAP's CMIP6 Fire Weather Index (FWI) for Alaska, 2040-2069, from the local data release (read-only).

Source: /import/beegfs/CMIP6/arctic-cmip6/cmip6_fwi/data_release_v2/cmip6_fwi/combined/cmip6_fwi_combined.nc
  = Rasdaman coverage cmip6_fwi (same dims: model 0-4 = CNRM-CM6-1-HR, EC-Earth3-Veg, MPI-ESM1-2-HR, MRI-ESM2-0, era5;
  daily, April-October only, 1980-04-01..2099-10-31, noleap; 0.25 deg lat/lon; SSP5-8.5 for the models).
  Young, Littell & Rupp 2025, USGS data release doi:10.5066/P1AAMRUF.
The file is uncompressed and contiguous (model, time, lat, lon), so it is read one model-year (214 full maps,
~87 MB) at a time and cut to the Alaska box. ERA5 has no future values and is skipped.

Output: <data>/fwi/fwi_alaska_2040-2069_ssp585.nc on the native 0.25 deg grid (Alaska box):
  fwi_mean[model, month, lat, lon]      mean daily FWI per calendar month (April..October), 2040-2069
  fwi_doy[model, day, lat, lon]         mean FWI on each day of the season (Apr 1 .. Oct 31, 214 days; noleap),
                                        2040-2069: input to the n-day rolling averages
  summer_days[model, rating, lat, lon]  mean days per summer (June-August) in each fire danger rating
                                        (Low < 9, Mod 9-18, High 18-28, VHigh 28-35, Ext >= 35; lower edge
                                        inclusive), as SNAP's API op=summer_fire_danger_rating_days
                                        (ua-snap/data-api luts.summer_fire_danger_ratings_dict["fwi"], from the
                                        Alaska Interagency Fire Danger Operating Plan, Table 1)
  python -I scripts/01_data/summarize_fwi.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import netCDF4
import numpy as np
import xarray as xr

from composite_indexing import config as C

SRC = Path("/import/beegfs/CMIP6/arctic-cmip6/cmip6_fwi/data_release_v2/cmip6_fwi/combined/cmip6_fwi_combined.nc")
OUT = C.DATA / "fwi" / "fwi_alaska_2040-2069_ssp585.nc"
MODELS = ["CNRM-CM6-1-HR", "EC-Earth3-Veg", "MPI-ESM1-2-HR", "MRI-ESM2-0"]  # indices 0-3 (4 = era5, historical only)
Y0, Y1 = 2040, 2069
LAT = (51.0, 72.5)  # Alaska box; the grid starts at -177 E, so the western Aleutians (west of 177 W) are not covered
LON = (-177.0, -129.0)
RATINGS = {"Low": (0, 9), "Mod": (9, 18), "High": (18, 28), "VHigh": (28, 35), "Ext": (35, np.inf)}
MONTHS = list(range(4, 11))
NDAY = 214  # April 1 .. October 31


def main():
    nc = netCDF4.Dataset(SRC)
    lat, lon = nc["lat"][:], nc["lon"][:]
    iy = np.where((lat >= LAT[0]) & (lat <= LAT[1]))[0]
    ix = np.where((lon >= LON[0]) & (lon <= LON[1]))[0]
    t = netCDF4.num2date(nc["time"][:], nc["time"].units, nc["time"].calendar)
    yr = np.array([d.year for d in t])
    mo = np.array([d.month for d in t])
    v = nc["fwi"]
    ny, nx = len(iy), len(ix)
    fmean = np.zeros((len(MODELS), len(MONTHS), ny, nx), "float64")
    nmon = np.zeros((len(MONTHS),), "int64")
    doy = np.zeros((len(MODELS), NDAY, ny, nx), "float64")
    summer = np.zeros((len(MODELS), len(RATINGS), ny, nx), "float64")
    for m, name in enumerate(MODELS):
        t0 = time.time()
        for y in range(Y0, Y1 + 1):
            ii = np.where(yr == y)[0]
            assert len(ii) == NDAY and np.all(np.diff(ii) == 1), (y, len(ii))
            block = np.asarray(v[m, ii[0]:ii[-1] + 1, :, :], "float32")[:, iy[0]:iy[-1] + 1, ix[0]:ix[-1] + 1]
            mm = mo[ii]
            for k, mon in enumerate(MONTHS):
                fmean[m, k] += block[mm == mon].sum(0)
                if m == 0:
                    nmon[k] += (mm == mon).sum()
            doy[m] += block
            jja = block[np.isin(mm, (6, 7, 8))]
            for k, (lo, hi) in enumerate(RATINGS.values()):
                summer[m, k] += ((jja >= lo) & (jja < hi)).sum(0)
        print(f"{name}: {time.time() - t0:.0f} s", flush=True)
    nyears = Y1 - Y0 + 1
    fmean /= nmon[None, :, None, None]
    doy /= nyears
    summer /= nyears
    # cells with no value (ocean, outside the data's domain) stay NaN; FWI NaNs are the same for every day
    blank = ~np.isfinite(fmean[:, 0])
    summer[np.broadcast_to(blank[:, None], summer.shape)] = np.nan
    ds = xr.Dataset(
        dict(fwi_mean=(("model", "month", "lat", "lon"), fmean.astype("float32"),
                       dict(long_name="mean daily Fire Weather Index", units="1")),
             fwi_doy=(("model", "day", "lat", "lon"), doy.astype("float32"),
                      dict(long_name="mean daily Fire Weather Index on each day of the season", units="1")),
             summer_days=(("model", "rating", "lat", "lon"), summer.astype("float32"),
                          dict(long_name="mean days per June-August with FWI in each fire danger rating",
                               units="days", bounds=str({k: list(v) for k, v in RATINGS.items()})))),
        coords=dict(model=MODELS, month=MONTHS, rating=list(RATINGS),
                    day=[d.strftime("%m-%d") for d in t[np.where(yr == Y0)[0]]], lat=lat[iy].astype("float64"),
                    lon=lon[ix].astype("float64")),
        attrs=dict(source=str(SRC), period=f"{Y0}-{Y1}", scenario="ssp585",
                   citation="Young, Littell & Rupp 2025, USGS data release doi:10.5066/P1AAMRUF",
                   days_per_month=str(dict(zip(MONTHS, (nmon // nyears).tolist())))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(OUT)
    print("wrote", OUT, ds.sizes)


if __name__ == "__main__":
    main()
