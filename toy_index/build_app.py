"""Toy index: pack the 1 km grids into one self-contained HTML app (toy_index/build/toy_index_app.html).

Each index is stored as a fixed-point uint16 code (0 = no value) split over the R (high byte) and G (low byte) channels
of an RGB PNG, embedded as a data URI; the page decodes it through a canvas. value = (code - 1) / scale - offset.
Two modes, switchable on screen: "raw" (future values, grids_1km.npz) and "delta" (change from a baseline,
grids_delta_1km.npz from build_delta.py). Default class breaks: statewide thirds of mapped land, except fixed
permafrost breaks (raw: team rule -1 / 0 degC; delta: 50 / 100 % progress to thaw, 100 % = crosses 0 degC).
A mode's index may carry an "na" code (maxcode + 1) for cells with a fixed class and no value (permafrost delta: ground
not frozen at the start = Low).
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

from composite_indexing import api
from composite_indexing import config as C

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "toy_index_app.html"
OUT_ARTIFACT = HERE / "build" / "toy_hazard_index.html"
GRIDS = C.DATA / "toy_index" / "grids_1km.npz"
DELTA = C.DATA / "toy_index" / "grids_delta_1km.npz"

MODES = {
    "raw": dict(label="Future values", indices={
        "wildfire": dict(name="Wildfire", offset=0, scale=1e5, unit="/yr", digits=4, range_q=(0, 0.995),
                         source="ALFRESCO relative flammability: average chance of burning per year",
                         details="2040–2069 · 5-model average · RCP 4.5"),
        "erosion": dict(name="Erosion", offset=0, scale=100, unit="in", digits=2, range_q=(0.005, 0.99),
                        source="DOT precipitation: rain in the 24-hour, 100-year storm",
                        details="2050–2079 · mean of GFDL-CM3 and NCAR-CCSM4 · RCP 8.5"),
        "permafrost": dict(name="Permafrost", offset=30, scale=100, unit="°C", digits=2, range_q=(0.005, 0.995),
                           source="GIPL 2.0 mean annual ground temperature at 1 m",
                           details="2040–2069 · 5-model average · RCP 4.5"),
    }),
    "delta": dict(label="Change over time", indices={
        "wildfire": dict(name="Wildfire", offset=0.05, scale=1e5, unit="/yr", digits=4, range_q=(0.005, 0.995),
                         signed=True, source="Change in ALFRESCO relative flammability (chance of burning per year)",
                         details="1980–2008 historical run → 2040–2069 · 5-model average · RCP 4.5"),
        "erosion": dict(name="Erosion", offset=100, scale=100, unit="%", digits=0, range_q=(0.005, 0.995),
                        signed=True, source="Change in rain in the 24-hour, 100-year storm",
                        details="NOAA Atlas 14 (model’s 1979–2005) → 2050–2079 · mean of GFDL-CM3 and NCAR-CCSM4 · "
                                "RCP 8.5"),
        "permafrost": dict(name="Permafrost", offset=200, scale=100, unit="%", digits=0, range_q=(0.005, 0.99),
                           clip=(-200, 400), na_label="not frozen at start", na_class=0,
                           source="Progress to thaw at 1 m: warming as a share of the distance to 0 °C "
                                  "(100 % = crosses 0 °C)",
                           details="2004–2015 → 2040–2069 · GIPL 2.0 · 5-model average · RCP 4.5 · "
                                   "ground not frozen at the start counts as Low"),
    }),
}
FIXED_BREAKS = {("raw", "permafrost"): [-1.0, 0.0], ("delta", "permafrost"): [50.0, 100.0]}
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


def huc_value(lat, lon):
    """Wildfire point values for a preset: SNAP API HUC-12 flammability, cached. raw = 2040-2069 5modelAvg rcp45;
    delta = raw minus 1980-2008 MODEL-SPINUP historical. Hosted pages can't call the API themselves, so presets carry
    them."""
    try:
        j = api.get_json(f"/alfresco/flammability/local/{lat:.4f}/{lon:.4f}", "toy_flam_local")
        raw = j["2040-2069"]["5modelAvg"]["rcp45"]
        return dict(raw=raw, delta=round(raw - j["1980-2008"]["MODEL-SPINUP"]["historical"], 6))
    except Exception as e:  # no watershed value (e.g. coast) or HTTP error
        print(f"  no HUC value at {lat}, {lon}: {e}")
        return None


def sig2(v):
    return float(f"{v:.2g}")


def png_b64(a, offset, scale, na=None):
    code = np.where(np.isfinite(a), np.round((a + offset) * scale) + 1, 0).astype(np.uint16)
    maxcode = int(code.max())
    if na is not None:  # fixed-class cells without a value
        code[na] = maxcode = maxcode + 1
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = code >> 8, code & 255
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), maxcode


def main():
    grids = dict(raw=np.load(GRIDS), delta=np.load(DELTA))
    land = grids["raw"]["land"]
    meta = dict(nx=C.GIPL_NX, ny=C.GIPL_NY, x0=C.GIPL_X0, ytop=C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES, res=C.GIPL_RES,
                modes={}, points=[])
    images = {}
    for mode, md in MODES.items():
        g = grids[mode]
        meta["modes"][mode] = dict(label=md["label"], indices={})
        for k, d in md["indices"].items():
            a = g[k].copy()
            a[~land] = np.nan
            if "clip" in d:
                a = np.clip(a, *d["clip"])
            na = land & g["permafrost_unfrozen_start"] if "na_label" in d else None
            v = a[land & np.isfinite(a)]
            images[f"{mode}-{k}"], maxcode = png_b64(a, d["offset"], d["scale"], na)
            lo, hi = np.quantile(v, d["range_q"])
            breaks = FIXED_BREAKS.get((mode, k)) or [sig2(q) for q in np.quantile(v, [1 / 3, 2 / 3])]
            if (mode, k) == ("delta", "wildfire"):  # thirds collapse on the many unchanged cells: Low = no increase,
                breaks = [0.0, sig2(np.median(v[v > 0]))]  # increases split at their median
            meta["modes"][mode]["indices"][k] = dict(d, range_q=None, clip=None, maxcode=maxcode, lo=float(lo),
                                                     hi=float(hi), breaks=breaks, na_code=maxcode if na is not None
                                                     else None)
            print(f"{mode} {k}: range {lo:.4g}..{hi:.4g}, breaks {breaks}, "
                  f"png {len(images[f'{mode}-{k}']) / 1e6:.2f} MB (base64)")
    g = grids["raw"]
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
        meta["points"].append(dict(name=name, lat=round(lat, 4), lon=round(lon, 4), x=round(x, 2), y=round(y, 2),
                                   huc=huc_value(round(lat, 4), round(lon, 4))))

    html = (HERE / "app_template.html").read_text()
    imgs = "\n".join(f'<img id="png-{k}" alt="" hidden src="data:image/png;base64,{b}">' for k, b in images.items())
    html = html.replace("<!--__IMAGES__-->", imgs).replace("/*__META__*/null", json.dumps(meta, ensure_ascii=False))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
    # claude.ai Artifact copy: the host adds the doctype/html/head/body skeleton, so the file starts at <title>
    head, rest = html.split("<title>", 1)
    body = rest.split("</head>", 1)
    art = "<title>" + body[0] + body[1].replace("<body>", "", 1).replace("</body>\n</html>", "")
    OUT_ARTIFACT.write_text(art)
    print(f"wrote {OUT_ARTIFACT}")


if __name__ == "__main__":
    main()
