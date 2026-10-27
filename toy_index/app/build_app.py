"""Toy index app: pack every variant (toy_index/<index>/variants/*) and preset (toy_index/composite/presets/*) into
the page app_template.html. Two outputs:

  build/toy_index_app.html   single file to download (tracked): data embedded as data URIs; only variants with
                             "in_single_file" (the page must stay under 16 MB, about six variants)
  build/hosted/              the claude.ai copy: index.html (no doctype/html/head/body; the host adds them) plus one
                             PNG per variant in data/, loaded only when someone picks the variant

Each variant is stored as a fixed-point uint16 code (0 = no value) split over the R (high byte) and G (low byte)
channels of an RGB PNG; the page decodes it through a canvas. value = (code - 1) / scale - offset. A variant with
fixed-class cells (na) gets code maxcode + 1 for them. Default breaks per variant.json ("thirds" = statewide thirds of
mapped land; "zero-median-increase" = Low is no increase, increases split at their median).
"""
import base64
import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent))

import numpy as np
import pyproj
from PIL import Image

from composite_indexing import api
from composite_indexing import config as C
from common import grid as G
from common import variant as V

OUT_SINGLE = HERE / "build" / "toy_index_app.html"
OUT_HOSTED = HERE / "build" / "hosted"
SNAP_KM = 15

POINTS = [  # (name, lat, lon); first = default
    ("Fort Wainwright", 64.8280, -147.6430),
    ("Fairbanks (downtown)", 64.8378, -147.7164),
    ("Delta Junction", 64.0379, -145.7322),
    ("Tok", 63.3367, -142.9856),
    ("Glennallen", 62.1092, -145.5464),
    ("Anchorage", 61.2181, -149.9003),
    ("Bethel", 60.7922, -161.7558),
    ("Dillingham", 59.0397, -158.4575),
    ("Nome", 64.5011, -165.4064),
    ("Kotzebue", 66.8983, -162.5966),
    ("Utqiaġvik", 71.2906, -156.7887),
    ("Juneau", 58.3019, -134.4197),
]


def sig2(v):
    return float(f"{v:.2g}")


def default_breaks(rule, v):
    if isinstance(rule, list):
        return rule
    if rule == "thirds":
        return [sig2(q) for q in np.quantile(v, [1 / 3, 2 / 3])]
    if rule == "zero-median-increase":
        return [0.0, sig2(np.median(v[v > 0]))]
    raise ValueError(f"unknown breaks rule {rule!r}")


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


def point_api_value(spec, lat, lon):
    """A variant's point value from the SNAP API (cached), e.g. the HUC-12 flammability average; None if absent."""
    def get(j, keys):
        for k in keys:
            j = j[k]
        return j
    try:
        j = api.get_json(spec["route"].format(lat=f"{lat:.4f}", lon=f"{lon:.4f}"), spec.get("cache_label", "toy_point_api"))
        v = get(j, spec["value"]) - (get(j, spec["minus"]) if "minus" in spec else 0)
        return round(v, 6)
    except Exception as e:  # no watershed value (e.g. coast) or HTTP error
        print(f"  no API value at {lat}, {lon}: {e}")
        return None


def main():
    land = G.land()
    meta = dict(nx=C.GIPL_NX, ny=C.GIPL_NY, x0=C.GIPL_X0, ytop=G.TOP, res=C.GIPL_RES,
                indices={k: dict(name=n, variants={}) for k, n in V.INDICES.items()}, presets=V.presets(), points=[])
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
            m, range_q=None, clip=None, sources=None, maxcode=maxcode, na_code=maxcode if na is not None else None,
            lo=float(lo), hi=float(hi), breaks=default_breaks(m["breaks"], vals))
        b = meta["indices"][v["index"]]["variants"][v["id"]]["breaks"]
        print(f"{key:40s} range {lo:.4g}..{hi:.4g}, breaks {b}, png {len(pngs[key]) / 1e6:.2f} MB")
    for p in meta["presets"]:
        for k, vid in p["variants"].items():
            assert vid in meta["indices"][k]["variants"], f"preset {p['id']}: unknown {k} variant {vid}"

    # Coastal towns often fall outside the land mask: move them to the nearest cell (<= SNAP_KM) that has values in
    # the default preset's erosion and permafrost variants, and say so in the name.
    fwd = pyproj.Transformer.from_crs(4326, 3338, always_xy=True)
    inv = pyproj.Transformer.from_crs(3338, 4326, always_xy=True)
    dv = meta["presets"][0]["variants"]
    ok = np.isfinite(grids[f"erosion/{dv['erosion']}"]) & np.isfinite(grids[f"permafrost/{dv['permafrost']}"])
    for name, lat, lon in POINTS:
        x, y = fwd.transform(lon, lat)
        c, r = int((x - meta["x0"]) // C.GIPL_RES), int((meta["ytop"] - y) // C.GIPL_RES)
        if not ok[r, c]:
            rr, cc = np.nonzero(ok[r - SNAP_KM:r + SNAP_KM + 1, c - SNAP_KM:c + SNAP_KM + 1])
            if not len(rr):
                print(f"dropped {name}: no data within {SNAP_KM} km")
                continue
            k = np.argmin((rr - SNAP_KM) ** 2 + (cc - SNAP_KM) ** 2)
            r, c = r - SNAP_KM + rr[k], c - SNAP_KM + cc[k]
            x, y = meta["x0"] + (c + 0.5) * C.GIPL_RES, meta["ytop"] - (r + 0.5) * C.GIPL_RES
            lon, lat = inv.transform(x, y)
            name = f"{name} (nearest data, {np.hypot(rr[k] - SNAP_KM, cc[k] - SNAP_KM):.0f} km)"
        lat, lon = round(lat, 4), round(lon, 4)
        apiv = {f"{i}/{vid}": point_api_value(vm["point_api"], lat, lon)
                for i, d in meta["indices"].items() for vid, vm in d["variants"].items() if vm.get("point_api")}
        meta["points"].append(dict(name=name, lat=lat, lon=lon, x=round(x, 2), y=round(y, 2), api=apiv))

    buf = io.BytesIO()
    Image.fromarray((land * 255).astype(np.uint8)).save(buf, "PNG", optimize=True)
    land_png = base64.b64encode(buf.getvalue()).decode()
    template = (HERE / "app_template.html").read_text()

    def page(srcs, embedded):
        mt = json.loads(json.dumps(meta))
        for i, d in mt["indices"].items():
            for vid, vm in d["variants"].items():
                vm["src"] = srcs.get(f"{i}/{vid}")
        imgs = [f'<img id="png-land" alt="" hidden src="data:image/png;base64,{land_png}">'] + [
            f'<img id="png-{k.replace("/", "--")}" alt="" hidden src="data:image/png;base64,'
            f'{base64.b64encode(pngs[k]).decode()}">' for k in embedded]
        return (template.replace("<!--__IMAGES__-->", "\n".join(imgs))
                .replace("/*__META__*/null", json.dumps(mt, ensure_ascii=False)))

    # single file: in_single_file variants embedded; the others are listed as "shared link only"
    single = [k for k in pngs if meta["indices"][k.split("/")[0]]["variants"][k.split("/")[1]].get("in_single_file")]
    for p in meta["presets"]:
        missing = [f"{k}/{vid}" for k, vid in p["variants"].items() if f"{k}/{vid}" not in single]
        if missing:
            print(f"  note: preset {p['id']} needs {missing}, not in the single file")
    html = page({k: "#png-" + k.replace("/", "--") for k in single}, single)
    OUT_SINGLE.parent.mkdir(exist_ok=True)
    OUT_SINGLE.write_text(html)
    print(f"wrote {OUT_SINGLE} ({OUT_SINGLE.stat().st_size / 1e6:.1f} MB, {len(single)} variants)")

    # hosted: every variant as its own file; the host adds the doctype/html/head/body skeleton, so start at <title>
    if OUT_HOSTED.exists():
        shutil.rmtree(OUT_HOSTED)
    (OUT_HOSTED / "data").mkdir(parents=True)
    srcs = {k: f"data/{k.replace('/', '--')}.png" for k in pngs}
    for k, b in pngs.items():
        (OUT_HOSTED / srcs[k]).write_bytes(b)
    html = page(srcs, [])
    head, rest = html.split("<title>", 1)
    body = rest.split("</head>", 1)
    (OUT_HOSTED / "index.html").write_text(
        "<title>" + body[0] + body[1].replace("<body>", "", 1).replace("</body>\n</html>", ""))
    size = sum(f.stat().st_size for f in OUT_HOSTED.rglob("*") if f.is_file())
    print(f"wrote {OUT_HOSTED}/ (index.html + {len(pngs)} variant files, {size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
