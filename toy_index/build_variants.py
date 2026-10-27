"""Build every variant's grid (toy_index/<index>/variants/<id>/build.py -> <data>/toy_index/variants/<index>/<id>.tif).

  python -I toy_index/build_variants.py                    # build the missing ones
  python -I toy_index/build_variants.py wildfire           # only this index (or wildfire/flam-change for one)
  python -I toy_index/build_variants.py --force [...]      # rebuild even if the file exists
Values are cut to the land mask; a quantile summary is printed per variant.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from common import grid as G
from common import variant as V


def main(args):
    force = "--force" in args
    picks = [a for a in args if not a.startswith("--")]
    land = G.land()
    for v in V.registry():
        key = f"{v['index']}/{v['id']}"
        if picks and not any(key == p or v["index"] == p for p in picks):
            continue
        if V.tif_path(v["index"], v["id"]).exists() and not force:
            print(f"{key:40s} exists (use --force to rebuild)")
            continue
        out = V.run_build(v)
        a, na = out["values"].astype("float32"), out.get("na")
        a[~land] = np.nan
        if na is not None:
            na = na & land
        V.save(v["index"], v["id"], a, na)
        q = np.nanquantile(a, [0, .1, .5, .9, 1])
        extra = f", {v['meta'].get('na_label', 'na')} {na[land].mean():.3f}" if na is not None else ""
        print(f"{key:40s} valid {np.isfinite(a)[land].mean():.3f}{extra}; q(0,10,50,90,100) {np.round(q, 4)}")


if __name__ == "__main__":
    main(sys.argv[1:])
