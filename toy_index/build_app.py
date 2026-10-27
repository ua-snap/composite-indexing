"""Toy index: pack the 1 km grids into one self-contained HTML app (toy_index/build/toy_index_app.html).

Each index is stored as a fixed-point uint16 code (0 = no value) split over the R (high byte) and G (low byte) channels
of an RGB PNG, embedded as a data URI; the page decodes it through a canvas. value = (code - 1) / scale - offset.
Default class breaks: statewide thirds of mapped land (wildfire, erosion); team rule -1 / 0 degC (permafrost).
"""
import base64
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pyproj
from PIL import Image

from composite_indexing import config as C

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "toy_index_app.html"
GRIDS = C.DATA / "toy_index" / "grids_1km.npz"

INDICES = {
    "wildfire": dict(name="Wildfire", offset=0, scale=1e5, unit="/yr", digits=4, range_q=(0, 0.995),
                     source="ALFRESCO relative flammability: average chance of burning per year",
                     details="2040–2069 · 5-model average · RCP 4.5"),
    "erosion": dict(name="Erosion", offset=0, scale=100, unit="in", digits=2, range_q=(0.005, 0.99),
                    source="DOT precipitation: rain in the 24-hour, 100-year storm",
                    details="2050–2079 · mean of GFDL-CM3 and NCAR-CCSM4 · RCP 8.5"),
    "permafrost": dict(name="Permafrost", offset=30, scale=100, unit="°C", digits=2, range_q=(0.005, 0.995),
                       source="GIPL 2.0 mean annual ground temperature at 1 m",
                       details="2040–2069 · 5-model average · RCP 4.5"),
}
FIXED_BREAKS = {"permafrost": [-1.0, 0.0]}
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


def png_b64(a, offset, scale):
    code = np.where(np.isfinite(a), np.round((a + offset) * scale) + 1, 0).astype(np.uint16)
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = code >> 8, code & 255
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), int(code.max())


def main():
    g = np.load(GRIDS)
    land = g["land"]
    meta = dict(nx=C.GIPL_NX, ny=C.GIPL_NY, x0=C.GIPL_X0, ytop=C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES, res=C.GIPL_RES,
                indices={}, points=[])
    images = {}
    for k, d in INDICES.items():
        a = g[k]
        v = a[land & np.isfinite(a)]
        images[k], maxcode = png_b64(a, d["offset"], d["scale"])
        lo, hi = np.quantile(v, d["range_q"])
        breaks = FIXED_BREAKS.get(k) or [sig2(q) for q in np.quantile(v, [1 / 3, 2 / 3])]
        meta["indices"][k] = dict(d, range_q=None, maxcode=maxcode, lo=float(lo), hi=float(hi), breaks=breaks)
        print(f"{k}: range {lo:.4g}..{hi:.4g}, breaks {breaks}, png {len(images[k]) / 1e6:.2f} MB (base64)")
    buf = io.BytesIO()
    Image.fromarray((land * 255).astype(np.uint8)).save(buf, "PNG", optimize=True)
    images["land"] = base64.b64encode(buf.getvalue()).decode()

    # Coastal towns often fall outside the GIPL land mask: move them to the nearest cell (<= SNAP_KM) that has both an
    # erosion and a permafrost value, and say so in the name.
    fwd = pyproj.Transformer.from_crs(4326, 3338, always_xy=True)
    inv = pyproj.Transformer.from_crs(3338, 4326, always_xy=True)
    ok = np.isfinite(g["erosion"]) & np.isfinite(g["permafrost"])
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
        meta["points"].append(dict(name=name, lat=round(lat, 4), lon=round(lon, 4), x=round(x, 2), y=round(y, 2)))

    html = (HERE / "app_template.html").read_text()
    imgs = "\n".join(f'<img id="png-{k}" alt="" hidden src="data:image/png;base64,{b}">' for k, b in images.items())
    html = html.replace("<!--__IMAGES__-->", imgs).replace("/*__META__*/null", json.dumps(meta, ensure_ascii=False))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
