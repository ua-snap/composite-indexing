"""Cached Rasdaman requests for the team workbench (merged from fetch_pilot.py and fetch_statewide.py; same requests, so
the cache still hits). Rules (CLAUDE.md): sequential, cached, never re-requested; new requests need the user's OK.

Approved and made 2026-10-27:
  - pilot: 100 x 100 km at Fairbanks, flammability + DOT pf for 6 durations x 2 models (13 requests, 2.1 MB)
  - statewide: flammability 2040-2069 (1 request, 19 MB), DOT 24 h pf 2 models x 4 strips (8 requests, ~165 MB),
    flammability 1980-2008 baseline (1 request, 19 MB)
GIPL comes from local GeoTIFFs (identical to the Rasdaman coverage), so it needs no requests.
"""
from composite_indexing import config as C
from composite_indexing import rasdaman as R

FAIRBANKS = (297_699, 1_667_062)  # EPSG:3338 (64.8378 N, 147.7164 W)
HALF = 50_000  # m, pilot window half-width

# Rasdaman encodings (DescribeCoverage ras:Encoding, saved in <data>/rasdaman_meta/)
FLAM = dict(era=3, model=1, scenario=1)  # 2040-2069, 5modelAvg, rcp45
FLAM_HIST = dict(era=1, model=0, scenario=0)  # 1980-2008, MODEL-SPINUP, historical
DOT_ERA = 1  # 2050-2079 (RCP 8.5 only)
DOT_MODELS = {"gfdlcm3": 0, "ncarccsm4": 1}
DOT_DURATIONS = {"60m": 12, "2h": 5, "3h": 8, "6h": 13, "12h": 1, "24h": 3}
DOT_DURATION = 3  # 24h
DOT_INTERVAL = 100  # return interval, years (axis is in years, not an index)

N_STRIPS = 4
X0, X1 = C.GIPL_X0, C.GIPL_X0 + C.GIPL_NX * C.GIPL_RES
Y0, Y1 = C.GIPL_Y0, C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES
FLAM_Y0 = 444_412.932644  # flammability coverage's southern edge (DescribeCoverage), north of the GIPL box edge


def window(x, y, half):
    """Bbox snapped to GIPL 1 km cell edges."""
    snap = lambda v: C.GIPL_X0 + round((v - C.GIPL_X0) / C.GIPL_RES) * C.GIPL_RES
    snapy = lambda v: C.GIPL_Y0 + round((v - C.GIPL_Y0) / C.GIPL_RES) * C.GIPL_RES
    return snap(x - half), snapy(y - half), snap(x + half), snapy(y + half)


def pilot_paths(fetch=False):
    x0, y0, x1, y1 = window(*FAIRBANKS, HALF)
    xy = [("X", x0, x1), ("Y", y0, y1)]
    paths = [R.get_coverage("alfresco_relative_flammability_30yr", [(k, v) for k, v in FLAM.items()] + xy,
                            label="toy_pilot_flam", fmt="image/tiff", fetch=fetch)]
    for m, mi in DOT_MODELS.items():
        for d, di in DOT_DURATIONS.items():
            subs = [("model", mi), ("duration", di), ("era", DOT_ERA), ("interval", DOT_INTERVAL)] + xy
            paths.append(R.get_coverage("dot_precip", subs, fields=["pf"], label=f"toy_pilot_{m}_{d}",
                                        fmt="image/tiff", fetch=fetch))
    return paths


def strips():
    step = (Y1 - Y0) / N_STRIPS
    return [(Y0 + i * step, Y0 + (i + 1) * step) for i in range(N_STRIPS)]


def flam_path(sel=FLAM, label="toy_state_flam", fetch=False):
    return R.get_coverage("alfresco_relative_flammability_30yr",
                          [(k, v) for k, v in sel.items()] + [("X", X0, X1), ("Y", max(Y0, FLAM_Y0), Y1)],
                          label=label, fmt="image/tiff", timeout=600, fetch=fetch)


def flam_hist_path(fetch=False):
    return flam_path(FLAM_HIST, "toy_state_flam_hist", fetch)


def dot_paths(fetch=False):
    out = {}
    for m, mi in DOT_MODELS.items():
        out[m] = [R.get_coverage("dot_precip", [("model", mi), ("duration", DOT_DURATION), ("era", DOT_ERA),
                                                ("interval", DOT_INTERVAL), ("X", X0, X1), ("Y", ya, yb)],
                                 fields=["pf"], label=f"toy_state_{m}_24h_s{i}", fmt="image/tiff", timeout=600,
                                 fetch=fetch)
                  for i, (ya, yb) in enumerate(strips())]
    return out
