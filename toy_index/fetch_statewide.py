"""Toy index: statewide Rasdaman slices (flammability, DOT 24 h 100-yr precip), cut to the GIPL 1 km box, cached.

Approved 2026-10-27: 9 requests, ~185 MB, sequential, cached via composite_indexing.rasdaman (never re-requested).
  - alfresco_relative_flammability_30yr: 1 request (~19 MB)
  - dot_precip pf, 2 models x 4 horizontal strips (~21 MB each)
GIPL comes from the local GeoTIFFs (no requests).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from composite_indexing import config as C
from composite_indexing import rasdaman as R

from fetch_pilot import DOT_ERA, DOT_INTERVAL, DOT_MODELS, FLAM

DOT_DURATION = 3  # 24h
N_STRIPS = 4
X0, X1 = C.GIPL_X0, C.GIPL_X0 + C.GIPL_NX * C.GIPL_RES
Y0, Y1 = C.GIPL_Y0, C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES
FLAM_Y0 = 444_412.932644  # flammability coverage's southern edge (DescribeCoverage), north of the GIPL box edge


def strips():
    step = (Y1 - Y0) / N_STRIPS
    return [(Y0 + i * step, Y0 + (i + 1) * step) for i in range(N_STRIPS)]


def flam_path():
    return R.get_coverage("alfresco_relative_flammability_30yr",
                          [(k, v) for k, v in FLAM.items()] + [("X", X0, X1), ("Y", max(Y0, FLAM_Y0), Y1)],
                          label="toy_state_flam", fmt="image/tiff", timeout=600)


def dot_paths():
    out = {}
    for m, mi in DOT_MODELS.items():
        out[m] = [R.get_coverage("dot_precip", [("model", mi), ("duration", DOT_DURATION), ("era", DOT_ERA),
                                                ("interval", DOT_INTERVAL), ("X", X0, X1), ("Y", ya, yb)],
                                 fields=["pf"], label=f"toy_state_{m}_24h_s{i}", fmt="image/tiff", timeout=600)
                  for i, (ya, yb) in enumerate(strips())]
    return out


def main():
    print(flam_path().name)
    for m, ps in dot_paths().items():
        for p in ps:
            print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
