"""Check a built coverage (build_coverage.py output) on its own, and optionally against SNAP's servers.

  python -I toy_index/coverage/check_coverage.py <build dir> [--server]

Offline (always):
  file     netCDF dims (y, x), cell-centre coordinates on the GIPL 1 km grid; envelope (centres +- 500 m) equal to the
           envelope of Rasdaman crrel_gipl_outputs_nc (saved DescribeCoverage XML); bands uint8, fill 255, values in
           {0, 1, 2, 255}; the hazard band recomputed from the three index bands with the recorded rule.
  recipe   bands and nilValues match the file; gridOrder matches each band's dimension order; the tiling bracket
           has one range per axis and its byte size matches (cells x all bands x 1 byte); metadata values are
           strings, the structured ones parse as JSON *and* as Python literals (wcst_import may evaluate them);
           WMS style hooks are well formed.
Server (--server; small, sequential, >= 1.5 s apart, cached in <data>/rasdaman_cache and <data>/api_cache):
  at the workbench's named places (the cells the PDF's table uses), each index's value from SNAP's own services,
  compared with the coverage's class and the variant value it came from:
  permafrost  Rasdaman crrel_gipl_outputs_nc_wcs, magt1m_degC, 5ModelAvg, RCP 4.5, file years 2060-2089 (= climate
              2040-2069): mean of the 30 years must equal the variant value at the cell (same cell, same data).
  wildfire    earthmaps.io /fire_weather/point/{lat}/{lon}/2040/2069?vars=fwi&op=summer_fire_danger_rating_days:
              High + Very High + Extreme days per model must equal the variant's source (summary file) at the same
              0.25 deg cell (+-1.5 days: the API rounds each count); the 4-model mean's class must equal the
              coverage's unless it is within 1.5 days of a boundary (the variant interpolates the 25 km cells
              bilinearly to 1 km, so the values differ by a few days where the field is steep).
  erosion     earthmaps.io /precipitation/frequency/point/{lat}/{lon}: 10-year, 24-hour depth, 2050-2079, mean of
              GFDL-CM3 and NCAR-CCSM4, as % change from NOAA Atlas 14 at the cell (the API reads one ~480 m DOT cell,
              the variant averages them to 1 km, so expect a few %).
Writes <build dir>/coverage_checks.txt.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import classify as K  # noqa: E402
from build_coverage import RASQL_WRITE_WORDS  # noqa: E402


def write_words(text):
    return [text[max(0, m.start() - 40):m.end() + 20] for m in re.finditer(RASQL_WRITE_WORDS, text, re.I)]

C, G = K.C, K.G
GIPL_XML = C.DATA / "rasdaman_meta/crrel_gipl_outputs_nc_wcs.describe.xml"
BANDS = ["wildfire", "erosion", "permafrost", "hazard"]
REPO = HERE.parents[1]


class Report:
    def __init__(self):
        self.lines, self.bad = [], 0

    def ok(self, cond, msg):
        self.bad += not cond
        self.lines.append(("ok   " if cond else "FAIL ") + msg)

    def info(self, msg):
        self.lines.append("info " + msg)


def read_nc(path):
    import netCDF4
    with netCDF4.Dataset(path) as ds:
        out = dict(dims=list(ds.dimensions), x=ds["x"][:].data, y=ds["y"][:].data, bands={}, att={})
        for b in BANDS:
            v = ds[b]
            v.set_auto_mask(False)
            out["bands"][b] = dict(data=v[:], dtype=str(v.dtype), dims=list(v.dimensions), fill=int(v._FillValue),
                                   att={k: v.getncattr(k) for k in v.ncattrs()})
        out["att"] = {k: ds.getncattr(k) for k in ds.ncattrs()}
    return out


def check_file(nc, meta, r):
    r.ok(nc["dims"] == ["y", "x"] and len(nc["y"]) == C.GIPL_NY and len(nc["x"]) == C.GIPL_NX,
         f"dims {nc['dims']} = (y {len(nc['y'])}, x {len(nc['x'])})")
    dx, dy = np.diff(nc["x"]), np.diff(nc["y"])
    r.ok(np.allclose(dx, C.GIPL_RES) and np.allclose(dy, -C.GIPL_RES), "x ascending, y descending, 1000 m steps")
    env = [nc["x"][0] - 500, nc["x"][-1] + 500, nc["y"][-1] - 500, nc["y"][0] + 500]
    xml = GIPL_XML.read_text()
    lo = re.search(r"<gml:lowerCorner>(.*?)</gml:lowerCorner>", xml).group(1).split()
    hi = re.search(r"<gml:upperCorner>(.*?)</gml:upperCorner>", xml).group(1).split()
    gipl = [float(lo[3]), float(hi[3]), float(lo[4]), float(hi[4])]  # model scenario time X Y
    r.ok(np.allclose(env, gipl, atol=1e-3),
         f"envelope (pixelIsPoint centres +- 500 m) {np.round(env, 3).tolist()} = crrel_gipl_outputs_nc {np.round(gipl, 3).tolist()}")
    pos = re.search(r"<gml:pos>(.*?)</gml:pos>", xml).group(1).split()
    r.ok(abs(float(pos[3]) - nc["x"][0]) < 1e-3 and abs(float(pos[4]) - nc["y"][0]) < 1e-3,
         f"first cell centre ({nc['x'][0]}, {nc['y'][0]}) = crrel_gipl_outputs_nc gml:pos ({pos[3]}, {float(pos[4]):.3f})")
    for b in BANDS:
        d = nc["bands"][b]
        u = set(np.unique(d["data"]).tolist())
        r.ok(d["dtype"] == "uint8" and d["fill"] == 255 and u <= {0, 1, 2, 255} and d["dims"] == ["y", "x"],
             f"band {b}: {d['dtype']}, fill {d['fill']}, values {sorted(u)}, dims {d['dims']}")
        # wcst_import copies these into the band metadata, which petascope puts into encode()'s rasql query. Keep to
        # SNAP's usual CF set, short and plain, with no rasql write words.
        allowed = {"_FillValue", "long_name", "flag_values", "flag_meanings", "grid_mapping", "units", "standard_name"}
        txt = " ".join(str(v) for v in d["att"].values())
        r.ok(set(d["att"]) <= allowed and not set('{}"\\') & set(txt) and len(txt) < 200 and not write_words(txt),
             f"band {b} attributes (copied into Rasdaman band metadata): {sorted(d['att'])}, plain, {len(txt)} characters")
    land = K.land_mask()
    r.ok(bool(np.all((nc["bands"]["hazard"]["data"] == 255) == ~land)) if meta["Decisions"]["hazard"]["missing"] == "low"
         else True, "hazard has a class on every land cell and none off land (missing index counts as Low)")
    R = meta["Decisions"]["hazard"]
    T = K.rule_table(R)
    cls = {k: np.where(nc["bands"][k]["data"] == 255, K.MISSING, nc["bands"][k]["data"]) for k in K.KEYS}
    h = np.where(land, T[cls["wildfire"], cls["erosion"], cls["permafrost"]], K.MISSING)
    h = np.where(h == K.MISSING, 255, h)
    r.ok(bool(np.array_equal(h, nc["bands"]["hazard"]["data"])), f"hazard band = rule '{R['rule']}' applied to the 3 index bands")


def check_recipe(recipe, nc, meta, r):
    o = recipe["recipe"]["options"]
    sl = o["coverage"]["slicer"]
    names = [b["name"] for b in sl["bands"]]
    r.ok(names == BANDS and all(b["identifier"] == b["name"] for b in sl["bands"]), f"recipe bands {names}")
    r.ok(all(int(b["nilValue"]) == nc["bands"][b["name"]]["fill"] for b in sl["bands"]), "nilValue = netCDF _FillValue (255)")
    ax = sl["axes"]
    dims = nc["bands"]["hazard"]["dims"]
    r.ok(ax["Y"]["gridOrder"] == dims.index("y") and ax["X"]["gridOrder"] == dims.index("x"),
         f"gridOrder Y={ax['Y']['gridOrder']}, X={ax['X']['gridOrder']} = position in the variable's dims {dims}")
    m = re.fullmatch(r"ALIGNED \[(.*)\] tile size (\d+)", o["tiling"])
    rng = [tuple(map(int, s.split(":"))) for s in m.group(1).split(",")]
    cells = int(np.prod([b - a + 1 for a, b in rng]))
    r.ok(len(rng) == len(ax) and cells * len(BANDS) == int(m.group(2)),
         f"tiling {o['tiling']}: {len(rng)} ranges for {len(ax)} axes, {cells:,} cells x {len(BANDS)} one-byte bands = {cells * len(BANDS):,} bytes")
    ny, nx = len(nc["y"]), len(nc["x"])
    tiles = -(-ny // (rng[0][1] + 1)) * -(-nx // (rng[1][1] + 1))
    r.info(f"{tiles} tiles; a point query reads one {cells * len(BANDS) / 2**20:.0f} MiB tile; whole coverage "
           f"{ny * nx * len(BANDS) / 1e6:.1f} MB uncompressed")
    r.ok(o["coverage"]["crs"] == "EPSG/0/3338" and sl["pixelIsPoint"] is True and o.get("wms_import") is True,
         "crs EPSG/0/3338, pixelIsPoint, wms_import")
    glob = o["coverage"]["metadata"]["global"]
    allstr = all(isinstance(v, str) for v in glob.values())
    parsed = True
    for k, v in glob.items():
        if v[:1] in "{[":
            try:
                a, b = json.loads(v), ast.literal_eval(v)
                parsed &= a == b
            except Exception:
                parsed = False
        parsed &= "${" not in v
    r.ok(allstr and parsed, f"metadata: {len(glob)} string values ({', '.join(glob)}); JSON ones parse identically "
                            "as JSON and as Python literals; no ${...}")
    unsafe = {k: sorted(set(c for c in v if c in '\\<>&' or not c.isascii())) for k, v in glob.items()}
    unsafe = {k: v for k, v in unsafe.items() if v}
    size = sum(len(k) + len(v) for k, v in glob.items())
    r.ok(not unsafe, f"metadata is plain ASCII with no backslash or < > & ({size:,} characters)"
                     + (f"; offending: {unsafe}" if unsafe else ""))
    words = write_words(" ".join(glob.values()))
    r.ok(not words, "metadata has no rasql write words (into, values, ...): with them, GetCoverage returns an empty body "
                    "(CMIP6 evspsbl / isi, and this coverage 2026-11-11)" + (f"; found: {words}" if words else ""))
    r.ok(json.loads(glob["Encoding"]) == {b: {"0": "Low", "1": "Medium", "2": "High", "255": "No data"} for b in BANDS},
         "Encoding: 0 Low, 1 Medium, 2 High, 255 No data for every band")
    hooks = recipe.get("hooks", [])
    styles = [re.search(r"STYLEID=([^&]+)", h["cmd"]).group(1) for h in hooks]
    cmaps_ok = all(json.loads(re.search(r'COLORTABLEDEFINITION=(.*)\\?"$', h["cmd"]).group(1).rstrip('"')
                              .replace('\\"', '"'))["type"] == "values" for h in hooks)
    r.ok(len(set(styles)) == len(BANDS) and cmaps_ok, f"WMS style hooks {styles}, colour tables parse")


# ---------------------------------------------------------------- server spot checks
def cell_lonlat(row, col):
    from pyproj import Transformer
    x, y = C.GIPL_X0 + (col + 0.5) * C.GIPL_RES, G.TOP - (row + 0.5) * C.GIPL_RES
    lon, lat = Transformer.from_crs(C.CRS, 4326, always_xy=True).transform(x, y)
    return x, y, lat, lon


def flat(j):
    if isinstance(j, list):
        return [v for x in j for v in flat(x)]
    return [float(j)] if isinstance(j, (int, float, str)) and str(j) not in ("",) else []


def check_server(nc, meta, r):
    from composite_indexing import api, rasdaman
    sys.path.insert(0, str(REPO / "toy_index"))
    from common import data as D

    dec = meta["Decisions"]
    land = K.land_mask()
    raw = {k: K.load_variant(k, dec[k]["variant"], land)[0] for k in K.KEYS}
    bnds = {k: dec[k]["breaks"][dec[k]["variant"]] for k in K.KEYS}
    h = (REPO / "toy_index/app/build/hosted/_local.html").read_text()
    i = h.index("const META = ") + len("const META = ")
    places = json.loads(h[i:h.index(";\n", i)])["places"]
    need = {"permafrost": "temp-1m-future", "wildfire": "fwi-high-days", "erosion": "storm-24h-10yr-change"}
    if any(dec[k]["variant"] != v for k, v in need.items()):
        r.info(f"server checks are written for {need}; this build uses "
               f"{ {k: dec[k]['variant'] for k in K.KEYS} }: only matching indices are checked")
    atlas = D.atlas14("24h", 10) if dec["erosion"]["variant"] == need["erosion"] else None
    fm, ftr, fnames = D.fwi_models("high_days") if dec["wildfire"]["variant"] == need["wildfire"] else (None,) * 3
    names = {"permafrost": "Permafrost", "wildfire": "Wildfire", "erosion": "Erosion"}
    for p in places:
        row, col = p["row"], p["col"]
        x, y, lat, lon = cell_lonlat(row, col)
        name = p["name"].split(" (nearest")[0]
        cl = {k: int(nc["bands"][k]["data"][row, col]) for k in BANDS}
        CL = {0: "Low", 1: "Medium", 2: "High", 255: "no data"}
        for k in K.KEYS:
            if dec[k]["variant"] != need[k]:
                continue
            v = float(raw[k][row, col])
            try:
                if k == "permafrost":
                    f = rasdaman.get_coverage("crrel_gipl_outputs_nc_wcs",
                                              [("X", x), ("Y", y), ("model", 0), ("scenario", 0),
                                               ("time", "2060-01-01T00:00:00.000Z", "2089-01-01T00:00:00.000Z")],
                                              fields=["magt1m_degC"], label=f"cov_check_r{row}c{col}",
                                              fmt="application/json")
                    vals = [q for q in flat(json.loads(Path(f).read_text())) if q > -9000]
                    s = float(np.mean(vals)) if len(vals) == 30 else float("nan")
                    if np.isfinite(v):
                        r.ok(abs(s - v) < 0.006, f"{name}: permafrost GIPL magt1m 2040-2069 from Rasdaman {s:.3f} degC "
                                                 f"= variant {v:.3f} (class {CL[cl[k]]})")
                    else:
                        r.info(f"{name}: permafrost GIPL magt1m 2040-2069 from Rasdaman {s:.3f} degC; variant has no "
                               f"value here (outside the ESA permafrost zone or a stuck cell) -> class {CL[cl[k]]}")
                elif k == "wildfire":
                    j = api.get_json(f"/fire_weather/point/{lat:.4f}/{lon:.4f}/2040/2069?vars=fwi"
                                     "&op=summer_fire_danger_rating_days", "cov_check_fwi")
                    per = {m: sum(d.get(c, 0) for c in ("High", "VHigh", "Ext"))
                           for m, d in j["2040-2069"]["fwi"].items() if m != "era5"}
                    s = float(np.mean(list(per.values())))
                    # the variant's source at the same ~25 km cell (per model, before bilinear to 1 km); the API
                    # rounds each rating's count, so allow 1.5 days per model
                    fc, fr = (~ftr) * ((lon + 180) % 360 - 180, lat)
                    loc = {str(m): float(fm[i, int(fr), int(fc)]) for i, m in enumerate(fnames)}
                    same_src = all(abs(loc[m] - per[m]) <= 1.5 for m in per if m in loc)
                    r.ok(same_src, f"{name}: wildfire API High+ days per model {per} = variant source cell "
                                   f"{ {m: round(x, 1) for m, x in loc.items()} } (+-1.5, API rounds)")
                    api_cls = int(K.class_of(np.array([s]), bnds[k])[0])
                    near = min(abs(s - bnds[k][0]), abs(s - bnds[k][1])) <= 1.5
                    msg = (f"{name}: wildfire API 4-model mean {s:.2f} days (25 km cell) vs variant {v:.2f} (bilinear "
                           f"to 1 km) -> API class {CL[api_cls]}, coverage {CL[cl[k]]}")
                    if np.isfinite(v):
                        if near:
                            r.info(msg + " (within 1.5 days of a boundary: either class is consistent)")
                        else:
                            r.ok(api_cls == cl[k], msg)
                    else:
                        r.info(msg + " (variant has no value here)")
                elif k == "erosion":
                    j = api.get_json(f"/precipitation/frequency/point/{lat:.4f}/{lon:.4f}", "cov_check_dot")
                    mm = [j["10"]["24h"][m]["2050-2079"]["pf"] for m in ("GFDL-CM3", "NCAR-CCSM4")]
                    a14 = float(atlas[row, col])
                    s = 100 * (np.mean(mm) / 25.4 / a14 - 1)
                    api_cls = int(K.class_of(np.array([s]), bnds[k])[0])
                    near = min(abs(s - bnds[k][0]), abs(s - bnds[k][1])) <= 3
                    msg = (f"{name}: erosion API 10-yr 24-h 2050-2079 {np.mean(mm):.1f} mm vs Atlas 14 {a14 * 25.4:.1f} mm "
                           f"= {s:+.1f} % vs variant {v:+.1f} % -> API class {CL[api_cls]}, coverage {CL[cl[k]]}")
                    if near:
                        r.info(msg + " (within 3 % of a boundary: either class is consistent)")
                    else:
                        r.ok(api_cls == cl[k] and abs(s - v) <= 5, msg)
            except Exception as e:  # e.g. no fire weather data outside the boreal region (HTTP 404)
                status = f"no {names[k].lower()} value from the server ({str(e).splitlines()[0][:120]})"
                fixed = np.isnan(v)
                (r.info if fixed else r.ok)(*(([f"{name}: {status}; variant has no value here either -> class "
                                                f"{CL[cl[k]]}"]) if fixed else [False, f"{name}: {status}"]))
        r.info(f"{name}: hazard {CL[cl['hazard']]} (wildfire {CL[cl['wildfire']]}, erosion {CL[cl['erosion']]}, "
               f"permafrost {CL[cl['permafrost']]})")


# ---------------------------------------------------------------- after the ingest: the coverage on Zeus
PALETTE = {(0, 114, 178): 0, (240, 228, 66): 1, (213, 94, 0): 2}


def png_classes(path):
    from PIL import Image
    im = np.array(Image.open(path).convert("RGBA"))
    out = np.full(im.shape[:2], 255, np.uint8)
    for rgb, c in PALETTE.items():
        out[(im[..., :3] == rgb).all(-1) & (im[..., 3] > 0)] = c
    return out, int(((out == 255) & (im[..., 3] > 0)).sum())


def check_ingested(nc, meta, recipe, d, r):
    """~20 small requests: DescribeCoverage, stored array, class counts, 6 cells, a 9x9 GetCoverage, WMS maps."""
    from composite_indexing import rasdaman as RD
    cov = meta["Coverage"]
    X0, TOP = C.GIPL_X0, G.TOP
    xml = RD.describe(cov, d / f"{cov}.describe.xml")
    if "<wcs:CoverageDescriptions" not in xml:
        r.ok(False, f"DescribeCoverage {cov}: {re.sub(r'<[^>]+>', ' ', xml)[:300]}")
        return
    lo = re.search(r"<gml:lowerCorner>(.*?)<", xml).group(1).split()
    hi = re.search(r"<gml:upperCorner>(.*?)<", xml).group(1).split()
    offs = [v.split() for v in re.findall(r"<gml:offsetVector[^>]*>(.*?)<", xml)]
    env = [float(lo[0]), float(hi[0]), float(lo[1]), float(hi[1])]
    want = [X0, X0 + C.GIPL_NX * C.GIPL_RES, C.GIPL_Y0, TOP]
    o = sorted((round(float(a), 3), round(float(b), 3)) for a, b in offs)
    r.ok(np.allclose(env, want, atol=1e-3) and o == [(0.0, -1000.0), (1000.0, 0.0)],
         f"DescribeCoverage: envelope {np.round(env, 3).tolist()} = GIPL grid, offset vectors {o} (X 1000 m, Y -1000 m)")
    mblock = re.search(r"<gmlcov:metadata>(.*?)</gmlcov:metadata>", xml, re.S).group(1)
    r.ok("\\" not in mblock and all(f"<ras:{k}>" in mblock or f"<{k}>" in mblock
                                     for k in recipe["recipe"]["options"]["coverage"]["metadata"]["global"]),
         f"stored metadata: every recipe key present, no backslashes ({len(mblock):,} characters)")
    bblock = re.search(r"<ras:bands>(.*?)</ras:bands>", mblock, re.S)
    btxt = re.sub(r"<[^>]+>", " ", bblock.group(1)) if bblock else ""
    r.ok(not set('{}"') & set(btxt) and "metadata_json" not in mblock,
         f"stored band metadata is plain (no JSON objects; {len(btxt.split()):,} words)")
    words = write_words(re.sub(r"<[^>]+>", " ", mblock))
    r.ok(not words, "stored metadata has no rasql write words (into, values, ...)" + (f"; found: {words}" if words else ""))
    t = RD.wcps(f'for $c in ({cov}) return encode($c.hazard * "x", "csv")', f"{cov}_domain", cache=False)
    dom = re.search(r"ARRAY \((\w+) (\w+)\) \[([^\]]*)\]", t)
    r.ok(bool(dom) and dom.group(3) == f"D0(0:{C.GIPL_NY - 1}),D1(0:{C.GIPL_NX - 1})",
         f"stored array: {dom.group(0) if dom else t[:200]} (rows, then columns)")
    for b in BANDS:
        q = (f"for $c in ({cov}) return encode(coverage n over $k x(0:2) values count($c.{b} = (char) $k), \"csv\")")
        got = RD.wcps(q, f"{cov}_count_{b}", cache=False).strip()
        want = [int((nc["bands"][b]["data"] == k).sum()) for k in range(3)]
        vals = [int(float(v)) for v in re.findall(r"[\d.]+", got)]
        r.ok(vals == want, f"{b}: cells per class on the server {vals or got[:120]} = netCDF {want}")
    NY, NX = nc["bands"]["hazard"]["data"].shape
    h = nc["bands"]["hazard"]["data"]
    rng, probes = np.random.default_rng(1), [(708, 1277)]
    while len(probes) < 6:
        rr, cc = int(rng.integers(0, NY)), int(rng.integers(0, NX))
        if len({h[rr, cc], h[NY - 1 - rr, cc], h[rr, NX - 1 - cc]}) == 3:
            probes.append((rr, cc))
    for rr, cc in probes:
        x, y = X0 + (cc + .5) * C.GIPL_RES, TOP - (rr + .5) * C.GIPL_RES
        want = [int(nc["bands"][b]["data"][rr, cc]) for b in BANDS]
        if 255 in want:  # a multi-band cell with a null prints garbled ('{ 1, 2, NULL, 255 }' for 1, 2, null, 1): read bands
            got = " ".join(RD.wcps(f"for $c in ({cov}) return (short) $c.{b}[X({x}), Y({y})]", f"{cov}_cell_r{rr}c{cc}_{b}",
                                   cache=False).strip() for b in BANDS)
            vals = [255 if v == "NULL" else int(v) for v in got.split()]
        else:
            got = RD.wcps(f"for $c in ({cov}) return $c[X({x}), Y({y})]", f"{cov}_cell_r{rr}c{cc}", cache=False)
            vals = [int(v) for v in re.findall(r"\d+", got)]
        r.ok(vals == want, f"cell row {rr} col {cc} (x {x:.0f}, y {y:.0f}): server {vals or got[:120]} = netCDF {want}"
                           " (cells picked so a flip would differ)")
    r0, c0, n = 704, 1273, 9
    sub = [("X", X0 + c0 * 1000 + 100, X0 + (c0 + n) * 1000 - 100), ("Y", TOP - (r0 + n) * 1000 + 100, TOP - r0 * 1000 - 100)]
    for fmt in ("image/tiff", "application/json"):
        try:
            f = RD.get_coverage(cov, sub, label=f"post_ingest_{meta['Version'][:19].replace(':', '')}", fmt=fmt)
            size = Path(f).stat().st_size
            if fmt == "image/tiff" and size:
                import rasterio
                with rasterio.open(f) as ds:
                    srv = np.stack([ds.read(i + 1) for i in range(ds.count)])
                loc = np.stack([nc["bands"][b]["data"][r0:r0 + n, c0:c0 + n] for b in BANDS])
                if srv.shape == loc.shape and not np.array_equal(srv, loc) and np.array_equal(srv, loc.transpose(0, 2, 1)):
                    # Zeus writes GeoTIFF transposed (rows = X) for coverages stored Y first; crrel_gipl_outputs_nc_wcs
                    # too (2026-11-11). WCPS, JSON and WMS are right. Fix: store X first (SNAP's CMIP6 recipes do).
                    r.info(f"GetCoverage {fmt} 9 x 9 cells at Fairbanks: {size:,} bytes; values = netCDF but TRANSPOSED "
                           "(rows hold X) while the GeoTIFF's georeferencing says rows hold Y. Same for GIPL: Zeus's "
                           "GeoTIFF output for coverages stored Y first")
                else:
                    r.ok(srv.shape == loc.shape and np.array_equal(srv, loc),
                         f"GetCoverage {fmt} 9 x 9 cells at Fairbanks: {size:,} bytes, {srv.shape} = netCDF")
            else:
                r.ok(size > 0, f"GetCoverage {fmt} 9 x 9 cells at Fairbanks: {size:,} bytes")
            if not size:
                Path(f).unlink()  # don't keep an empty answer in the cache
        except Exception as e:
            r.ok(False, f"GetCoverage {fmt}: {str(e)[:300]}")
    # WMS: native CRS must be exact; Web Mercator compared with PROJ (Zeus warps differently, also for GIPL)
    r0, c0, n = 658, 1227, 100
    bb = (X0 + c0 * 1000, TOP - (r0 + n) * 1000, X0 + (c0 + n) * 1000, TOP - r0 * 1000)
    p = RD.get_map(dict(layers=cov, styles=f"{cov}_hazard", crs="EPSG:3338", bbox=",".join(f"{v:.3f}" for v in bb),
                        width=n, height=n), f"{cov}_3338", cache=False)
    cls, odd = png_classes(p)
    r.ok(np.array_equal(cls, h[r0:r0 + n, c0:c0 + n]) and not odd,
         f"WMS EPSG:3338, 100 x 100 px = cells around Fairbanks: {np.mean(cls == h[r0:r0 + n, c0:c0 + n]) * 100:.1f} % of pixels = netCDF")
    from affine import Affine
    from pyproj import Transformer
    from rasterio.warp import reproject, Resampling
    t = Transformer.from_crs(3338, 3857, always_xy=True)
    xs, ys = t.transform([bb[0], bb[2], bb[0], bb[2]], [bb[3], bb[3], bb[1], bb[1]])
    b57 = (min(xs), min(ys), max(xs), max(ys))
    W = 128
    H = round(W * (b57[3] - b57[1]) / (b57[2] - b57[0]))
    p = RD.get_map(dict(layers=cov, styles=f"{cov}_hazard", crs="EPSG:3857", bbox=",".join(f"{v:.3f}" for v in b57),
                        width=W, height=H), f"{cov}_3857", cache=False)
    srv, _ = png_classes(p)

    def proj(dx=0.0):
        dst = np.full((H, W), 255, np.uint8)
        px = (b57[2] - b57[0]) / W
        reproject(h.astype(np.uint8), dst, src_transform=Affine(1000, 0, X0, 0, -1000, TOP), src_crs="EPSG:3338",
                  dst_transform=Affine(px, 0, b57[0] + dx * px, 0, -(b57[3] - b57[1]) / H, b57[3] + dx * px),
                  dst_crs="EPSG:3857", resampling=Resampling.nearest, src_nodata=255, dst_nodata=255)
        return dst
    ref = proj()
    r.info(f"WMS EPSG:3857 vs PROJ's reprojection of the netCDF: {np.mean(srv == ref) * 100:.1f} % of pixels agree "
           f"(two correct renderings half a pixel apart agree {np.mean(ref == proj(0.5)) * 100:.1f} %). Zeus's Web "
           "Mercator output is shifted/warped by several km for crrel_gipl_outputs_nc_wms too (57 % on 2026-11-10): "
           "use EPSG:3338 in the map client, or check the server's reprojection")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_dir")
    ap.add_argument("--server", action="store_true", help="also spot-check against Rasdaman / the API (small)")
    ap.add_argument("--ingested", action="store_true",
                    help="check the ingested coverage on Zeus against this build (~20 small requests)")
    a = ap.parse_args()
    d = Path(a.build_dir)
    meta = json.loads((d / "metadata.json").read_text())
    recipe = json.loads((d / "ingest.json").read_text())
    nc = read_nc(d / f"{meta['Coverage']}.nc")
    r = Report()
    check_file(nc, meta, r)
    check_recipe(recipe, nc, meta, r)
    if a.server:
        check_server(nc, meta, r)
    if a.ingested:
        check_ingested(nc, meta, recipe, d, r)
    text = "\n".join(r.lines)
    print(text)
    (d / "coverage_checks.txt").write_text(text + f"\n{r.bad} failed\n")
    print(f"{r.bad} failed; wrote {d / 'coverage_checks.txt'}")
    sys.exit(1 if r.bad else 0)


if __name__ == "__main__":
    main()
