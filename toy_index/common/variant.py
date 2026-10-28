"""The variant contract: one candidate version of one index.

Repo:  toy_index/<index>/variants/<id>/variant.json   description (fields below)
       toy_index/<index>/variants/<id>/build.py       build() -> dict(values=float32 grid, na=bool grid or None)
Data:  <data>/toy_index/variants/<index>/<id>.tif     band 1 values (NaN = no value); band 2 (if any) na mask

variant.json fields
  letter         the variant's name in the app: "A", "B", ... (unique within the index; never reused)
  label          short name shown under the letter, e.g. "Flammability, change"
  description    one line: what a value means
  details        periods · models · scenario
  method         how it's computed, in words, enough to rebuild it (shown in the app and the PDF export)
  unit, digits   display (digits also sets the slider/number step)
  offset, scale  app encoding: code = round((value + offset) * scale) + 1 must fit in 1..65534
  range_q        [lo, hi] quantiles of land values for the histogram/slider range
  breaks         [b1, b2] fixed defaults, or "thirds" (statewide thirds of mapped land), or "zero-median-increase"
                 (Low = no increase; increases split at their median)
  signed         show a "+" on positive values (changes)
  clip           [lo, hi] clip values for the app (classes still right if the breaks lie inside)
  na_label, na_class   cells flagged in band 2: no value, fixed class (0 Low, 1 Medium, 2 High), shown as na_label
  point_api      watershed point value from the SNAP API instead of the pixel: {route, value: [keys], minus: [keys]}
  status         draft | candidate | recommended | retired (retired variants are left out of the app)
  sources, author, created
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import rasterio

from composite_indexing import config as C

from . import grid as G

ROOT = Path(__file__).resolve().parents[1]  # toy_index/
INDICES = {"wildfire": "Wildfire", "erosion": "Erosion", "permafrost": "Permafrost"}
DATA_DIR = C.DATA / "toy_index" / "variants"


def tif_path(index, vid):
    return DATA_DIR / index / f"{vid}.tif"


def registry():
    """All variants: list of dict(index, id, dir, meta), in index order then folder name."""
    out = []
    for index in INDICES:
        for f in sorted((ROOT / index / "variants").glob("*/variant.json")):
            out.append(dict(index=index, id=f.parent.name, dir=f.parent, meta=json.loads(f.read_text())))
    return out


def index_info(index):
    """toy_index/<index>/index.json: name, question (index "composite" = the Environmental Hazard)."""
    return json.loads((ROOT / index / "index.json").read_text())


def decisions():
    """The repo copy of the team decisions (composite/decisions.json): per index {variant, breaks, note}, and
    "hazard" (the combining rule). The app starts from these until the team saves its own."""
    return json.loads((ROOT / "composite" / "decisions.json").read_text())


def run_build(v):
    spec = importlib.util.spec_from_file_location(f"variant_{v['index']}_{v['id']}", v["dir"] / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()


def save(index, vid, values, na=None):
    p = tif_path(index, vid)
    p.parent.mkdir(parents=True, exist_ok=True)
    bands = [values.astype("float32")] + ([na.astype("float32")] if na is not None else [])
    with rasterio.open(p, "w", driver="GTiff", height=G.SHAPE[0], width=G.SHAPE[1], count=len(bands),
                       dtype="float32", crs=C.CRS, transform=G.GRID, nodata=np.nan, compress="deflate") as ds:
        for i, b in enumerate(bands, 1):
            ds.write(b, i)
    return p


def sig2(v):
    return float(f"{v:.2g}")


def default_breaks(rule, v):
    """[b1, b2] from variant.json "breaks" over the mapped land values v (see the field list above)."""
    if isinstance(rule, list):
        return rule
    if rule == "thirds":
        return [sig2(q) for q in np.quantile(v, [1 / 3, 2 / 3])]
    if rule == "zero-median-increase":
        return [0.0, sig2(np.median(v[v > 0]))]
    raise ValueError(f"unknown breaks rule {rule!r}")


def load(index, vid):
    """(values, na) on the GIPL grid; na is None when the variant has no fixed-class cells."""
    with rasterio.open(tif_path(index, vid)) as ds:
        values = ds.read(1)
        na = ds.read(2) > 0.5 if ds.count > 1 else None
    return values, na
