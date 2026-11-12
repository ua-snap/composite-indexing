"""Low / Medium / High classes exactly as the team workbench computes them (app_template.html).

The app reads each variant as a fixed-point code (build_app.py: code = round((value + offset) * scale) + 1, from the
float32 variant GeoTIFF cut to the land mask and clipped), decodes value = (code - 1) / scale - offset, and classes
it: Low if value <= b1, Medium if value <= b2, else High (with a 1e-9 tolerance, so a value on a boundary goes to the
lower class). Fixed-class cells (variant band 2, e.g. "outside the boreal area") take na_class. Land cells with no
value are MISSING. The combining rule (ruleClass) turns the three classes into the hazard class. Using the same codes
makes the coverage match the app and the PDF cell for cell; full_precision_classes() gives the classes without the
encoding step, to count how many cells the encoding moves across a boundary.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent))

from composite_indexing import config as C  # noqa: E402
from common import grid as G  # noqa: E402
from common import variant as V  # noqa: E402

KEYS = ["wildfire", "erosion", "permafrost"]
LOW, MED, HIGH, MISSING, SEA = 0, 1, 2, 3, 255
EPS = 1e-9
REGIONS_TIF = C.DATA / "features/regions_1km.tif"
REGION_NAMES = ["Arctic", "Interior", "West", "South"]


def variant_meta(index, vid):
    d = V.ROOT / index / "variants" / vid / "variant.json"
    if not d.exists():
        raise FileNotFoundError(f"{index} variant {vid!r} is not in the repo ({d})")
    return json.loads(d.read_text())


def load_variant(index, vid, land):
    """(raw values float32 with NaN off land / no value, na mask or None, app codes int64 with 0 = no value)."""
    m = variant_meta(index, vid)
    a, na = V.load(index, vid)
    a = a.copy()
    a[~land] = np.nan
    if m.get("clip"):
        a = np.clip(a, *m["clip"])
    code = np.where(np.isfinite(a), np.round((a + m["offset"]) * m["scale"]) + 1, 0).astype(np.int64)  # = build_app
    return a, na, code


def class_of(v, b):
    return np.where(v <= b[0] + EPS, LOW, np.where(v <= b[1] + EPS, MED, HIGH))


def classes(index, vid, b, land):
    """App-identical class grid: 0-2, MISSING (land, no value), SEA (off land)."""
    m = variant_meta(index, vid)
    a, na, code = load_variant(index, vid, land)
    v = (code - 1) / m["scale"] - m["offset"]  # float64, as in the browser
    out = np.full(land.shape, SEA, np.uint8)
    out[land] = MISSING
    ok = land & (code > 0)
    out[ok] = class_of(v[ok], b)
    if na is not None:
        out[land & na] = m["na_class"]
    return out


def full_precision_classes(index, vid, b, land):
    m = variant_meta(index, vid)
    a, na, _ = load_variant(index, vid, land)
    out = np.full(land.shape, SEA, np.uint8)
    out[land] = MISSING
    ok = land & np.isfinite(a)
    out[ok] = class_of(a[ok].astype(np.float64), b)
    if na is not None:
        out[land & na] = m["na_class"]
    return out


def rule_class(R, w, e, p):
    """app_template.html ruleClass: classes 0-2 or MISSING -> hazard class 0-2 or MISSING."""
    c = [w, e, p]
    if all(x == MISSING for x in c):
        return MISSING
    if MISSING in c:
        if R["missing"] == "blank":
            return MISSING
        c = [0 if x == MISSING else x for x in c]
    pts = [x + 1 for x in c]
    rule = R["rule"]
    if rule == "worst":
        return max(c)
    if rule == "avg":
        wt = [float(R["weights"][k]) for k in KEYS]
        sw = sum(wt)
        score = sum(x * y for x, y in zip(pts, wt)) / sw if sw > 0 else 1
        return 0 if score < R["avgCuts"][0] - EPS else 1 if score < R["avgCuts"][1] - EPS else 2
    if rule == "product":
        pr = pts[0] * pts[1] * pts[2]
        return 0 if pr <= R["prodCuts"][0] else 1 if pr <= R["prodCuts"][1] else 2
    if rule == "count":
        nh, nm = sum(x == 2 for x in c), sum(x >= 1 for x in c)
        return 2 if nh >= R["countHigh"] else 1 if nm >= R["countMed"] else 0
    if rule == "custom":
        return R["custom"][c[0] * 9 + c[1] * 3 + c[2]]
    raise ValueError(f"unknown combining rule {rule!r}")


def rule_table(R):
    """[4, 4, 4] lookup over (wildfire, erosion, permafrost) classes incl. MISSING (3)."""
    T = np.zeros((4, 4, 4), np.uint8)
    for w in range(4):
        for e in range(4):
            for p in range(4):
                T[w, e, p] = rule_class(R, w, e, p)
    return T


def hazard(cls, R, land):
    """cls: {index: class grid}. Hazard class grid (0-2, MISSING, SEA)."""
    T = rule_table(R)
    h = np.full(land.shape, SEA, np.uint8)
    h[land] = T[cls["wildfire"][land], cls["erosion"][land], cls["permafrost"][land]]
    return h


def regions():
    import rasterio
    with rasterio.open(REGIONS_TIF) as ds:
        return ds.read(1)


def area_counts(arr, reg):
    """[area][class 0-3] like the app: area 0 statewide, 1-4 regions; MISSING counted, SEA not."""
    n = np.zeros((5, 4), np.int64)
    for c in range(4):
        sel = arr == c
        n[0, c] = sel.sum()
        for r in range(1, 5):
            n[r, c] = (sel & (reg == r)).sum()
    return n


def land_mask():
    return G.land()
