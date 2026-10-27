"""Toy index pilot: one 100 x 100 km window around Fairbanks from Rasdaman (flammability, DOT precip), cached.

Approved pilot (2026-10-27): ~14 small GeoTIFF requests, sequential, cached via composite_indexing.rasdaman.
GIPL comes from the local GeoTIFFs (identical to the Rasdaman coverage), so it needs no requests.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from composite_indexing import config as C
from composite_indexing import rasdaman as R

FAIRBANKS = (297_699, 1_667_062)  # EPSG:3338 (64.8378 N, 147.7164 W)
HALF = 50_000  # m

# Rasdaman encodings (DescribeCoverage ras:Encoding, saved in <data>/rasdaman_meta/)
FLAM = dict(era=3, model=1, scenario=1)  # 2040-2069, 5modelAvg, rcp45
DOT_ERA = 1  # 2050-2079 (RCP 8.5 only)
DOT_MODELS = {"gfdlcm3": 0, "ncarccsm4": 1}
DOT_DURATIONS = {"60m": 12, "2h": 5, "3h": 8, "6h": 13, "12h": 1, "24h": 3}
DOT_INTERVAL = 100  # return interval, years (axis is in years, not an index)


def window(x, y, half):
    """Bbox snapped to GIPL 1 km cell edges."""
    snap = lambda v: C.GIPL_X0 + round((v - C.GIPL_X0) / C.GIPL_RES) * C.GIPL_RES
    snapy = lambda v: C.GIPL_Y0 + round((v - C.GIPL_Y0) / C.GIPL_RES) * C.GIPL_RES
    return snap(x - half), snapy(y - half), snap(x + half), snapy(y + half)


def main():
    x0, y0, x1, y1 = window(*FAIRBANKS, HALF)
    xy = [("X", x0, x1), ("Y", y0, y1)]
    paths = [R.get_coverage("alfresco_relative_flammability_30yr", [(k, v) for k, v in FLAM.items()] + xy,
                            label="toy_pilot_flam", fmt="image/tiff")]
    for m, mi in DOT_MODELS.items():
        for d, di in DOT_DURATIONS.items():
            subs = [("model", mi), ("duration", di), ("era", DOT_ERA), ("interval", DOT_INTERVAL)] + xy
            paths.append(R.get_coverage("dot_precip", subs, fields=["pf"], label=f"toy_pilot_{m}_{d}",
                                        fmt="image/tiff"))
    for p in paths:
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
