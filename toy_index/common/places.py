"""Named places shown in the app's place list, snapped to the nearest cell with data."""
import numpy as np
import pyproj

from composite_indexing import api
from composite_indexing import config as C

from . import grid as G
from . import variant as V

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


def default_ok():
    """Cells with values in the repo's chosen erosion and permafrost variants (the app snaps places to these)."""
    d = V.decisions()
    ok = G.land()
    for k in ("erosion", "permafrost"):
        ok &= np.isfinite(V.load(k, d[k]["variant"])[0])
    return ok


def snapped(ok):
    """Places as dict(name, lat, lon, x, y, row, col). Coastal towns often fall outside the land mask: move them to
    the nearest cell (<= SNAP_KM) where `ok`, and say so in the name; drop them if there is none."""
    fwd = pyproj.Transformer.from_crs(4326, 3338, always_xy=True)
    inv = pyproj.Transformer.from_crs(3338, 4326, always_xy=True)
    out = []
    for name, lat, lon in POINTS:
        x, y = fwd.transform(lon, lat)
        c, r = int((x - C.GIPL_X0) // C.GIPL_RES), int((G.TOP - y) // C.GIPL_RES)
        if not ok[r, c]:
            rr, cc = np.nonzero(ok[r - SNAP_KM:r + SNAP_KM + 1, c - SNAP_KM:c + SNAP_KM + 1])
            if not len(rr):
                print(f"dropped {name}: no data within {SNAP_KM} km")
                continue
            k = np.argmin((rr - SNAP_KM) ** 2 + (cc - SNAP_KM) ** 2)
            r, c = r - SNAP_KM + rr[k], c - SNAP_KM + cc[k]
            x, y = C.GIPL_X0 + (c + 0.5) * C.GIPL_RES, G.TOP - (r + 0.5) * C.GIPL_RES
            lon, lat = inv.transform(x, y)
            name = f"{name} (nearest data, {np.hypot(rr[k] - SNAP_KM, cc[k] - SNAP_KM):.0f} km)"
        out.append(dict(name=name, lat=round(lat, 4), lon=round(lon, 4), x=round(x, 2), y=round(y, 2),
                        row=int(r), col=int(c)))
    return out


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
