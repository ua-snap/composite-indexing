"""Four broad regions on the GIPL 1 km grid, from the physiographic names of the USDA STATSGO2 Alaska (2016) map units
(the first part of each map-unit name, e.g. "Interior Alaska Lowlands-Boreal Upland-..."), grouped as:
  1 Arctic, 2 Interior, 3 West, 4 South.
Output: <data>/features/regions_1km.tif (uint8, 0 = none) + regions_legend.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from composite_indexing import config as C

SG = C.DATA / "statsgo2/extracted/wss_gsmsoil_AK_2016-10-13"
OUT = C.DATA / "features"
REGIONS = {
    1: ("Arctic", ["Arctic Coastal Plain", "Arctic Foothills", "Northern Brooks Range Mountains",
                   "Interior Brooks Range Mountains", "Western Brooks Range Mountains, Foothills, and Valleys"]),
    2: ("Interior", ["Interior Alaska Highlands", "Interior Alaska Lowlands", "Interior Alaska Mountains", "Yukon Flats",
                     "Upper Kobuk and Koyukuk Hills and Valleys"]),
    3: ("West", ["Yukon-Kuskokwim", "Seward Peninsula Highlands", "Northern Seward Peninsula", "Nulato Hills",
                 "Bristol Bay", "Ahklun Mountains", "Northern Bering Sea Islands"]),
    4: ("South", ["Copper River Basin", "Cook Inlet Mountains", "Cook Inlet Lowlands", "Southern Alaska Coastal Mountains",
                  "Southern Alaska Peninsula Mountains", "Alexander Archipelago", "Aleutian Islands"]),
}


def region_of(muname):
    for code, (_, prefixes) in REGIONS.items():
        if any(muname.startswith(p) for p in prefixes):
            return code
    return 0


def main():
    cols = pd.read_csv(SG / "tabular/mstabcol.txt", sep="|", header=None, quotechar='"', usecols=[0, 1, 2])
    names = cols[cols[0] == "mapunit"].sort_values(1)[2].tolist()
    mu = pd.read_csv(SG / "tabular/mapunit.txt", sep="|", header=None, names=names, quotechar='"', dtype={"mukey": str})
    mu["region"] = mu.muname.map(region_of)
    missing = mu[mu.region == 0].muname.tolist()
    assert not missing, f"unassigned map units: {missing[:5]}"
    shp = gpd.read_file(SG / "spatial/gsmsoilmu_a_ak.shp").to_crs(C.CRS)
    shp["region"] = shp.MUKEY.astype(str).map(dict(zip(mu.mukey, mu.region)))
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        prof = s.profile
    r = rasterize(((g, int(k)) for g, k in zip(shp.geometry, shp.region)), out_shape=(prof["height"], prof["width"]),
                  transform=prof["transform"], fill=0, dtype="uint8")
    OUT.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT / "regions_1km.tif", "w", **dict(prof, dtype="uint8", nodata=0, compress="lzw")) as d:
        d.write(r, 1)
    pd.DataFrame([dict(code=k, region=v[0], statsgo_regions="; ".join(v[1])) for k, v in REGIONS.items()]).to_csv(
        OUT / "regions_legend.csv", index=False)
    print({v[0]: int((r == k).sum()) for k, v in REGIONS.items()})


if __name__ == "__main__":
    main()
