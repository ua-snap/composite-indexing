"""Why does GIPL's ground surface warm differently from the air (PTI V2 vs V1)?

Hypothesis: snow insulates the ground in winter, so winter air warming reaches the ground surface only partly. Then
V2 - V1 should be more negative where air warming is concentrated in winter.
Per permafrost cell (PTI domain, GIPL usable): air warming by season (DJF, JJA; SNAP 2 km 5modelAvg, era minus
2014-2023), the winter share of warming, and the V2 - V1 warming difference (index_variants.nc).
Output: <data>/results/t4/seasonal_warming.csv (regional medians + Spearman of V2-V1 vs winter excess).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from scipy.stats import spearmanr

from composite_indexing import config as C
from t1_maat_vs_magt import TAS, cell_centres, read, to_gipl

RES = C.DATA / "results/t4"
REGIONS = {0: "Statewide", 1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
SEASONS = {"DJF": [12, 1, 2], "JJA": [6, 7, 8]}
ERAS = {"2051_2080": (2051, 2080), "2081_2100": (2081, 2100)}


def season_mean(scen, months, y0, y1):
    acc, n = 0.0, 0
    for y in range(y0, y1 + 1):
        for m in months:
            acc, n = acc + read(TAS / f"5modelAvg_{scen}" / f"tas_mean_C_AR5_5modelAvg_{scen}_{m:02d}_{y}.tif"), n + 1
    return acc / n


def main():
    v = xr.open_dataset(RES / "index_variants.nc")
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg, prof = s.read(1), s.profile
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        good = s.read(1) == 2
    X, Y = cell_centres(prof)
    today = v["T_N1_rcp85_2051_2080"].values
    dom = np.isfinite(today) & good
    rows = []
    for scen in ["rcp45", "rcp85"]:
        ref = {k: to_gipl(season_mean(scen, ms, 2014, 2023), X, Y) for k, ms in SEASONS.items()}
        for era, (y0, y1) in ERAS.items():
            d = {k: to_gipl(season_mean(scen, ms, y0, y1), X, Y) - ref[k] for k, ms in SEASONS.items()}
            diff = v[f"T_G2_{scen}_{era}"].values - v[f"T_N2_{scen}_{era}"].values  # V2 - V1 warming
            excess = d["DJF"] - d["JJA"]  # how much more winter warms than summer
            for k, rn in REGIONS.items():
                m = dom & ((reg == k) if k else True) & np.isfinite(excess) & np.isfinite(diff)
                rows.append(dict(scen=scen, era=era, region=rn, n=int(m.sum()),
                                 winter_warming=np.median(d["DJF"][m]), summer_warming=np.median(d["JJA"][m]),
                                 winter_minus_summer=np.median(excess[m]), v2_minus_v1=np.median(diff[m]),
                                 spearman_diff_vs_winter_excess=spearmanr(diff[m][::5], excess[m][::5]).statistic))
            print(scen, era, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "seasonal_warming.csv", index=False)
    with pd.option_context("display.width", 200):
        print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
