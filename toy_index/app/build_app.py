"""Team workbench: pack every variant (toy_index/<index>/variants/*), the index questions (<index>/index.json)
and the repo's decisions (composite/decisions.json) into the page app_template.html.

  python -I toy_index/app/build_app.py
Output build/hosted/ (git-ignored): index.html for claude.ai (no doctype/html/head/body; the host adds them), _local.html
(the same page as a full document, for local tests), and one PNG per variant in data/, loaded when its index tab opens.
Publish index.html with data/*.png and capabilities {db: {}, user: {scopes: ["profile"]}} (team decisions).

Each variant is stored as a fixed-point uint16 code (0 = no value) split over the R (high byte) and G (low byte)
channels of an RGB PNG; the page decodes it through a canvas. value = (code - 1) / scale - offset. A variant with
fixed-class cells (na) gets code maxcode + 1 for them. The land mask (R) and regions (G: 1 Arctic, 2 Interior, 3 West,
4 South) travel in one embedded PNG. Default breaks per variant.json (see common/variant.py).
"""
import base64
import io
import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent))

import numpy as np
import rasterio
from PIL import Image

from composite_indexing import config as C
from common import grid as G
from common import places as P
from common import variant as V

OUT = HERE / "build" / "hosted"
REGIONS = C.DATA / "features/regions_1km.tif"


def png_bytes(a, offset, scale, na=None):
    code = np.where(np.isfinite(a), np.round((a + offset) * scale) + 1, 0)
    assert code.max() < 65535, "values don't fit the encoding: change offset/scale (or clip) in variant.json"
    code = code.astype(np.uint16)
    maxcode = int(code.max())
    if na is not None:  # fixed-class cells without a value
        code[na] = maxcode = maxcode + 1
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = code >> 8, code & 255
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "PNG", optimize=True)
    return buf.getvalue(), maxcode


def base_png(land):
    with rasterio.open(REGIONS) as ds:
        reg = ds.read(1)
    rgb = np.zeros(land.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = land * 255, np.where(land, reg, 0)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    land = G.land()
    dec = V.decisions()
    meta = dict(nx=C.GIPL_NX, ny=C.GIPL_NY, x0=C.GIPL_X0, ytop=G.TOP, res=C.GIPL_RES, built=time.strftime("%Y-%m-%d"),
                regions=["Arctic", "Interior", "West", "South"], hazard=V.index_info("composite"), decisions=dec,
                indices={k: dict(V.index_info(k), variants={}) for k in V.INDICES}, places=[])
    pngs, grids = {}, {}
    for v in V.registry():
        m, key = v["meta"], f"{v['index']}/{v['id']}"
        if m.get("status") == "retired":
            continue
        a, na = V.load(v["index"], v["id"])
        a = a.copy()
        a[~land] = np.nan
        if m.get("clip"):
            a = np.clip(a, *m["clip"])
        grids[key] = a
        vals = a[land & np.isfinite(a)]
        pngs[key], maxcode = png_bytes(a, m["offset"], m["scale"], na)
        lo, hi = np.quantile(vals, m["range_q"])
        meta["indices"][v["index"]]["variants"][v["id"]] = dict(
            m, range_q=None, clip=None, maxcode=maxcode, na_code=maxcode if na is not None else None,
            lo=float(lo), hi=float(hi), breaks=V.default_breaks(m["breaks"], vals), src=f"data/{key.replace('/', '--')}.png")
        b = meta["indices"][v["index"]]["variants"][v["id"]]["breaks"]
        print(f"{key:40s} {m['letter']} range {lo:.4g}..{hi:.4g}, breaks {b}, png {len(pngs[key]) / 1e6:.2f} MB")
    for k, d in meta["indices"].items():
        letters = [vm["letter"] for vm in d["variants"].values()]
        assert len(set(letters)) == len(letters), f"{k}: duplicate variant letters {letters}"
        assert dec[k]["variant"] in d["variants"], f"decisions.json: unknown {k} variant {dec[k]['variant']}"
        d["variants"] = dict(sorted(d["variants"].items(), key=lambda kv: kv[1]["letter"]))

    # Places snap to the nearest cell with values in the repo's chosen erosion and permafrost variants.
    ok = np.isfinite(grids[f"erosion/{dec['erosion']['variant']}"]) & np.isfinite(grids[f"permafrost/{dec['permafrost']['variant']}"])
    for p in P.snapped(ok):
        apiv = {f"{i}/{vid}": P.point_api_value(vm["point_api"], p["lat"], p["lon"])
                for i, d in meta["indices"].items() for vid, vm in d["variants"].items() if vm.get("point_api")}
        meta["places"].append(dict(p, api=apiv))

    template = (HERE / "app_template.html").read_text()
    html = (template.replace("<!--__BASE__-->", f'<img id="png-base" alt="" hidden src="data:image/png;base64,{base_png(land)}">')
            .replace("/*__META__*/null", json.dumps(meta, ensure_ascii=False)))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    for k, b in pngs.items():
        (OUT / f"data/{k.replace('/', '--')}.png").write_bytes(b)
    (OUT / "_local.html").write_text(html)
    # claude.ai adds the doctype/html/head/body skeleton, so the published page starts at <title>
    head, rest = html.split("<title>", 1)
    body = rest.split("</head>", 1)
    (OUT / "index.html").write_text(
        "<title>" + body[0] + body[1].replace("<body>", "", 1).replace("</body>\n</html>", ""))
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file() and f.name != "_local.html")
    print(f"wrote {OUT}/ (index.html + {len(pngs)} variant files, {size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
