"""Team workbench PDF -> Rasdaman coverage: a 4-band netCDF (wildfire, erosion, permafrost, hazard classes), its
wcst_import ingest recipe and a build record.

  python -I toy_index/coverage/build_coverage.py <workbench.pdf> [--coverage-id ID] [--out DIR] [--server-dir DIR]
                                                 [--force]

Steps
  1. Read the PDF's decision record (read_pdf.py): the variant and boundaries per index, and the combining rule.
  2. Check the record against the repo: each variant exists, its letter matches variant.json, boundaries are ordered,
     the rule's parameters are complete.
  3. Class every 1 km cell exactly as the app does (classify.py) and combine with the rule.
  4. Check the result against the numbers printed in the same PDF: shares of land per index and for the hazard,
     the hazard by region, the named places, all 27 rule combinations. Stops on any mismatch (unless --force).
  5. Write <out>/<ID>.nc, <out>/ingest.json (wcst_import general_coverage recipe), <out>/metadata.json (the
     metadata in both), <out>/decisions.json (the record), <out>/build_checks.txt, and a copy of the PDF.
     Also copies the recipe to toy_index/coverage/ingest/ingest.json (the current recipe in the repo).

Band values: 0 Low, 1 Medium, 2 High, 255 no data (outside the GIPL land mask, or a land cell where the index has
no value, e.g. stuck GIPL cells). The hazard never has 255 on land when the rule counts a missing index as Low.
Grid: the GIPL 2.0 1 km grid (EPSG:3338), identical cells to Rasdaman crrel_gipl_outputs_nc.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import classify as K  # noqa: E402
import read_pdf  # noqa: E402

C, G, V = K.C, K.G, K.V
REPO = HERE.parents[1]
DEFAULT_ID = "environmental_hazard_index_test"
NODATA = 255
BANDS = ["wildfire", "erosion", "permafrost", "hazard"]
NAMES = {"wildfire": "Wildfire", "erosion": "Erosion", "permafrost": "Permafrost", "hazard": "Environmental Hazard"}
CLASS_NAMES = {"0": "Low", "1": "Medium", "2": "High", "255": "No data"}
RULE_NAMES = {"worst": "Worst of the three", "avg": "Average of points (weighted)",
              "product": "Multiply points (Wildfire x Erosion x Permafrost)", "count": "Count the Highs",
              "custom": "Custom table (set each combination)"}
# WMS colours: the app's class palette (Okabe-Ito blue / yellow / vermillion), no data transparent
COLORS = {"0": [0, 114, 178, 255], "1": [240, 228, 66, 255], "2": [213, 94, 0, 255], "255": [0, 0, 0, 0]}
TILE = 512  # square XY tiles: 512 x 512 cells x 4 one-byte bands = 1 MiB (rasdaman-audit tiling guide: 1-4 MB)


def band_attrs(b):
    """The band variable's attributes (besides _FillValue): all wcst_import copies into the band metadata."""
    return dict(long_name=f"{NAMES[b]} class", flag_values=np.array([0, 1, 2], np.uint8),
                flag_meanings="low medium high", grid_mapping="crs")


# ---------------------------------------------------------------- record checks
def check_record(rec):
    errs = []
    for k in K.KEYS:
        d = rec.get(k) or {}
        vid = d.get("variant")
        try:
            m = K.variant_meta(k, vid)
        except FileNotFoundError as e:
            errs.append(str(e))
            continue
        if m.get("status") == "retired":
            errs.append(f"{k}: variant {vid} is retired in the repo")
        if d.get("letter") != m["letter"]:
            errs.append(f"{k}: PDF says Variant {d.get('letter')} for {vid}, repo variant.json says {m['letter']}")
        b = (d.get("breaks") or {}).get(vid)
        if not (isinstance(b, list) and len(b) == 2 and all(isinstance(x, (int, float)) for x in b) and b[0] <= b[1]):
            errs.append(f"{k}: boundaries for {vid} missing or not ordered: {b}")
        if not V.tif_path(k, vid).exists():
            errs.append(f"{k}: variant grid not built: {V.tif_path(k, vid)}")
    R = rec.get("hazard") or {}
    need = {"worst": [], "avg": ["weights", "avgCuts"], "product": ["prodCuts"], "count": ["countHigh", "countMed"],
            "custom": ["custom"]}
    if R.get("rule") not in need:
        errs.append(f"hazard: unknown rule {R.get('rule')!r}")
    else:
        for f in need[R["rule"]] + ["missing"]:
            if R.get(f) is None:
                errs.append(f"hazard: rule {R['rule']} needs {f}")
        if R["rule"] == "custom" and len(R.get("custom") or []) != 27:
            errs.append("hazard: custom table must have 27 entries")
    if R.get("missing") not in ("low", "blank"):
        errs.append(f"hazard: unknown missing rule {R.get('missing')!r}")
    return errs


# ---------------------------------------------------------------- checks against the PDF's printed numbers
def app_places():
    """Named places (name, row, col, api values) from the workbench build the PDF came from."""
    h = (REPO / "toy_index/app/build/hosted/_local.html").read_text()
    i = h.index("const META = ") + len("const META = ")
    return json.loads(h[i:h.index(";\n", i)])["places"]


def check_against_pdf(cls, haz, rec, printed, reg):
    """Returns (lines, n_failed)."""
    out, bad = [], 0

    def ok(cond, msg):
        nonlocal bad
        bad += not cond
        out.append(("ok   " if cond else "FAIL ") + msg)

    def near(x, shown):  # PDF prints Math.round / toFixed(0) of a percentage; "<1 %" read as 0.4
        return abs(x - shown) <= 0.5 + 1e-6 or (shown == 0.4 and 0 < x < 0.5)

    for k in K.KEYS:
        n = K.area_counts(cls[k], reg)[0]
        s = 100 * n / n.sum()
        shown = printed["index_shares"][k]
        okk = all(near(s[c], shown[c]) for c in range(3)) and (near(s[3], shown[3]) if shown[3] else s[3] < 0.5)
        ok(okk, f"{k} share of land (L/M/H/no value %): coverage {s.round(2).tolist()} vs PDF {shown}")
    n = K.area_counts(haz, reg)
    s = 100 * n[0] / n[0].sum()
    ok(all(near(s[c], printed["hazard_shares"][c]) for c in range(3)),
       f"hazard share of land: coverage {s.round(2).tolist()} vs PDF {printed['hazard_shares']}")
    for i, rn in enumerate(K.REGION_NAMES, 1):
        r = 100 * n[i][:3] / n[i].sum()
        ok(all(near(r[c], printed["hazard_regions"][rn][c]) for c in range(3)),
           f"hazard in {rn} (L/M/H %): coverage {r.round(2).tolist()} vs PDF {printed['hazard_regions'][rn]}")
    T = K.rule_table(rec["hazard"])
    comb = printed["combinations"]
    ok(len(comb) == 27 and all(T[a, b, c] == v for (a, b, c), v in comb.items()),
       f"rule: all 27 combinations agree with the PDF ({len(comb)} read)")
    places = {p["name"].split(" (nearest data")[0]: p for p in app_places()}
    for name, shown in printed["places"].items():
        p = places.get(name)
        if p is None:
            ok(False, f"place {name}: not in the app build")
            continue
        got = [int(cls[k][p["row"], p["col"]]) for k in K.KEYS] + [int(haz[p["row"], p["col"]])]
        api_idx = [i for i, k in enumerate(K.KEYS) if f"{k}/{rec[k]['variant']}" in (p.get("api") or {})]
        if api_idx:  # the app shows a watershed value from the SNAP API there, not the cell: compare the rest
            keep = [i for i in range(3) if i not in api_idx]
            ok(all(got[i] == shown[i] for i in keep),
               f"place {name}: cells {got[:3]} vs PDF {shown[:3]} (index {api_idx} from the API in the app: skipped)")
        else:
            ok(got == shown, f"place {name} (row {p['row']}, col {p['col']}): coverage {got} vs PDF {shown}")
    return out, bad


# ---------------------------------------------------------------- metadata
def fmt_num(x):
    return f"{x:g}"


def band_meta(k, rec):
    vid = rec[k]["variant"]
    m, b = K.variant_meta(k, vid), rec[k]["breaks"][vid]
    u = m["unit"]
    d = dict(
        band=k, index=NAMES[k], variant=vid, variant_letter=m["letter"], variant_label=m["label"],
        description=m["description"], details=m["details"], method=m.get("method", m["description"]),
        unit=u, low_upper_bound=b[0], medium_upper_bound=b[1],
        classes=(f"Low: value at most {fmt_num(b[0])} {u}; Medium: more than {fmt_num(b[0])} and at most "
                 f"{fmt_num(b[1])} {u}; High: more than {fmt_num(b[1])} {u}"),
        no_data="255: outside the land mask, or no value for this index at the cell",
        sources=m.get("sources", []), repo_variant=f"toy_index/{k}/variants/{vid}",
        high_means=rec[k].get("high", ""), low_means=rec[k].get("low", ""), team_decision=bool(rec[k].get("decided")))
    if m.get("na_label"):
        d["fixed_class"] = f"cells {m['na_label']} have no value and are classed {CLASS_NAMES[str(m['na_class'])]}"
    return d


def rule_text(R):
    w = R.get("weights") or {}
    return {
        "worst": "Hazard = the highest of the three classes.",
        "avg": (f"Score each index Low 1, Medium 2, High 3; weighted average (weights: Wildfire {w.get('wildfire')}, "
                f"Erosion {w.get('erosion')}, Permafrost {w.get('permafrost')}). Low if score < {R.get('avgCuts', [0])[0]}; "
                f"High if score >= {R.get('avgCuts', [0, 0])[1]}; otherwise Medium."),
        "product": (f"Score each index Low 1, Medium 2, High 3 and multiply (1 to 27). Low if product <= "
                    f"{R.get('prodCuts', [0])[0]}; Medium if <= {R.get('prodCuts', [0, 0])[1]}; otherwise High."),
        "count": (f"High if at least {R.get('countHigh')} of the three indices are High; otherwise Medium if at least "
                  f"{R.get('countMed')} are Medium or High; otherwise Low."),
        "custom": "Each of the 27 combinations set by hand (see combinations).",
    }[R["rule"]]


def hazard_meta(R):
    T = K.rule_table(R)
    combos = {"".join("LMH"[i] for i in (a, b, c)): "LMH"[T[a, b, c]]
              for a in range(3) for b in range(3) for c in range(3)}
    params = {k: R[k] for k in ("weights", "avgCuts", "prodCuts", "countHigh", "countMed") if R["rule"] in
              {"weights": ["avg"], "avgCuts": ["avg"], "prodCuts": ["product"], "countHigh": ["count"],
               "countMed": ["count"]}[k]}
    return dict(
        band="hazard", index=NAMES["hazard"], rule=R["rule"], rule_name=RULE_NAMES[R["rule"]], rule_text=rule_text(R),
        rule_parameters=params,
        missing=("an index with no value counts as Low; if all three have no value, the hazard has none (255)"
                 if R["missing"] == "low" else "if any index has no value, the hazard has none (255)"),
        combinations=combos, combinations_key="Wildfire, Erosion, Permafrost classes (L/M/H) -> hazard class",
        no_data="255: outside the land mask" + ("" if R["missing"] == "low" else ", or an index has no value"),
        high_means=R.get("high", ""), low_means=R.get("low", ""), team_decision=bool(R.get("decided")))


def git_rev():
    try:
        rev = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True).stdout.strip()
        br = subprocess.run(["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True,
                            text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "toy_index"], capture_output=True,
                               text=True).stdout.strip()
        return f"{br}@{rev}" + (" (uncommitted changes)" if dirty else "")
    except Exception:
        return "unknown"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_metadata(cov, rec, pdf_info, built):
    bands = {k: band_meta(k, rec) for k in K.KEYS}
    bands["hazard"] = hazard_meta(rec["hazard"])
    decided = sum(bool(rec[k].get("decided")) for k in K.KEYS + ["hazard"])
    x1 = C.GIPL_X0 + C.GIPL_NX * C.GIPL_RES
    grid = dict(crs="EPSG:3338", resolution_m=C.GIPL_RES, columns=C.GIPL_NX, rows=C.GIPL_NY,
                x_edges=[C.GIPL_X0, x1], y_edges=[C.GIPL_Y0, G.TOP],
                note="GIPL 2.0 1 km grid: the same cells as Rasdaman crrel_gipl_outputs_nc; land = GIPL land mask")
    source = dict(pdf=pdf_info["file"], pdf_sha256=pdf_info["sha256"], exported_utc=rec.get("exported"),
                  app_data_built=rec.get("data_built"), team_decisions=f"{decided} of 4",
                  variant_grids={k: {"file": V.tif_path(k, rec[k]["variant"]).name,
                                     "sha256": sha256(V.tif_path(k, rec[k]["variant"]))} for k in K.KEYS},
                  code=f"composite-indexing {git_rev()}: toy_index/coverage/build_coverage.py")
    decisions = {k: {f: rec[k][f] for f in ("variant", "letter", "breaks", "decided")} for k in K.KEYS}
    decisions["hazard"] = {f: v for f, v in rec["hazard"].items() if f not in ("note", "high", "low")}
    return _clean({
        "Title": "Environmental Hazard Index for Alaska, 1 km (TEST: team decisions are not final)",
        "Abstract": ("Low / Medium / High classes for three hazard indices (wildfire, erosion, permafrost) and the "
                     "combined Environmental Hazard, on a 1 km grid over Alaska (EPSG:3338). Each index puts every "
                     "cell in a class using a variant and boundaries chosen by the team in the Environmental Hazard "
                     "Index workbench; the combining rule then gives the hazard class. TEST "
                     "coverage for front-end development: the decisions, and so the classes, will change."),
        "Status": "test",
        "Version": built,
        "Institution": "Scenarios Network for Alaska and Arctic Planning (SNAP), University of Alaska Fairbanks",
        "Encoding": {b: CLASS_NAMES for b in BANDS},
        "Bands": bands,
        "Decisions": decisions,
        "Grid": grid,
        "Source": source,
        "Coverage": cov,
    })


RECIPE_SKIP = {"Decisions": None, "Source": "variant_grids"}  # in the netCDF only: repeats Bands / long checksums


def recipe_metadata(meta):
    out = {}
    for k, v in meta.items():
        if k in RECIPE_SKIP and RECIPE_SKIP[k] is None:
            continue
        if k in RECIPE_SKIP:
            v = {a: b for a, b in v.items() if a != RECIPE_SKIP[k]}
        out[k] = recipe_value(v)
    return out


_ASCII = [("→", " to "), ("->", " to "), ("≤", " at most "), ("≥", " at least "), ("<=", " at most "),
          (">=", " at least "), ("<", " less than "), (">", " more than "), ("&", " and "), ("–", "-"), ("—", "-"),
          ("−", "-"), ("°C", " degC"), ("°", " deg"), ("×", "x"), ("÷", "/"),
          (" · ", "; "), ("·", ";"), ("±", "+/-"), ("‘", "'"), ("’", "'"),
          ("“", "'"), ("”", "'"), ('"', "'"), ("\\", "/"), ("\n", " "), ("…", "...")]


# Rasdaman query words for writing. Petascope puts the coverage metadata inside the rasql query of every encode()
# (GetCoverage JSON / GeoTIFF / netCDF, WCPS encode). With "into" in a description, SNAP's CMIP6 evspsbl and fire
# weather isi coverages returned empty GetCoverage bodies until the descriptions were reworded (2025-10), and so did
# this coverage (Abstract "... into the hazard class", 2026-11-11). Metadata text must not contain them.
RASQL_WRITE_WORDS = r"\b(into|insert|update|delete|drop|create|alter|values|commit)\b"
_WORDS = [(r"\binto\b", "to"), (r"\bvalues\b", "data")]


def ascii_text(s):
    """Metadata text that survives Rasdaman: ASCII only, no backslash or double quote (they become escapes in
    encode()'s options), no < > & (XML), none of the rasql write words above."""
    import unicodedata
    s = re.sub(r"<(\w+)>", lambda m: m.group(1).upper(), s)  # file-name placeholders: pcpt_<model>_ -> pcpt_MODEL_
    for a, b in _WORDS:
        s = re.sub(a, b, s, flags=re.I)
    for a, b in _ASCII:
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r" {2,}", " ", s).strip()


def _clean(v):
    """Recursively: ascii_text() on strings; JSON true/false/null -> "yes"/"no"/"" (wcst_import may evaluate a value
    as a Python literal, README)."""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if v is None:
        return ""
    if isinstance(v, str):
        return ascii_text(v)
    if isinstance(v, dict):
        return {ascii_text(k): _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def recipe_value(v):
    """Recipe metadata values: plain text as is; structures as compact JSON text. Both without backslashes."""
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=True, separators=(",", ":"))
    assert "\\" not in s and s.isascii() and not set("<>&") & set(s), f"unsafe metadata value: {s[:200]}"
    bad = re.search(RASQL_WRITE_WORDS, s, re.I)
    assert not bad, f"rasql write word {bad.group(0)!r} in metadata: ...{s[max(0, bad.start() - 80):bad.end() + 40]}..."
    return s


# ---------------------------------------------------------------- outputs
def write_nc(path, arrays, meta):
    import netCDF4
    from pyproj import CRS

    x = C.GIPL_X0 + C.GIPL_RES * (np.arange(C.GIPL_NX) + 0.5)
    y = G.TOP - C.GIPL_RES * (np.arange(C.GIPL_NY) + 0.5)
    tmp = path.with_suffix(".nc.part")
    with netCDF4.Dataset(tmp, "w", format="NETCDF4") as ds:
        ds.createDimension("y", len(y))
        ds.createDimension("x", len(x))
        vx = ds.createVariable("x", "f8", ("x",))
        vx[:] = x
        vx.setncatts(dict(standard_name="projection_x_coordinate", long_name="x coordinate of cell centre",
                          units="m", axis="X"))
        vy = ds.createVariable("y", "f8", ("y",))
        vy[:] = y
        vy.setncatts(dict(standard_name="projection_y_coordinate", long_name="y coordinate of cell centre",
                          units="m", axis="Y"))
        crs = ds.createVariable("crs", "i4")
        crs.setncatts({**CRS.from_epsg(3338).to_cf(), "epsg_code": "EPSG:3338"})
        # wcst_import copies every attribute of the band and grid-mapping variables into the coverage metadata (only
        # the global metadata is set by the recipe). Petascope puts band metadata into encode()'s format options, and
        # the first two ingests, whose bands carried a JSON object (metadata_json) and a long comment, returned an
        # empty body for every GetCoverage (JSON, GeoTIFF, netCDF). So band attributes are kept to SNAP's usual CF
        # set (DOT's: long_name, _FillValue, grid_mapping) plus the flags; per-band details go in global attributes.
        band_text = {}
        for b in BANDS:
            bm = meta["Bands"][b]
            v = ds.createVariable(b, "u1", ("y", "x"), zlib=True, complevel=4, fill_value=np.uint8(NODATA),
                                  chunksizes=(TILE, TILE))
            v[:] = arrays[b]
            v.setncatts(band_attrs(b))
            band_text[f"{b}_comment"] = (
                f"{bm['rule_text']} {bm['missing']}" if b == "hazard" else
                f"Variant {bm['variant_letter']} ({bm['variant']}): {bm['description']}. {bm['classes']}."
                + (f" {bm['fixed_class'][0].upper()}{bm['fixed_class'][1:]}." if bm.get("fixed_class") else ""))
            band_text[f"{b}_metadata_json"] = json.dumps(bm, ensure_ascii=True)
        ds.setncatts(band_text)
        ds.setncatts({"Conventions": "CF-1.8", "title": meta["Title"], "summary": meta["Abstract"],
                      "status": meta["Status"], "institution": meta["Institution"], "date_created": meta["Version"],
                      "source_pdf": meta["Source"]["pdf"], "source_pdf_sha256": meta["Source"]["pdf_sha256"],
                      "team_decisions_exported": meta["Source"]["exported_utc"] or "",
                      "history": f"{meta['Version']} {meta['Source']['code']}",
                      "class_encoding": json.dumps(CLASS_NAMES), "decisions_json": json.dumps(meta["Decisions"]),
                      "grid": json.dumps(meta["Grid"]), "coverage_id": meta["Coverage"]})
    tmp.rename(path)


def style_hook(cov, band):
    abstract = f"{NAMES[band]} class (Low / Medium / High)"
    wcps = f"$c.{band}"
    cmap = json.dumps({"type": "values", "colorTable": COLORS}, separators=(",", ":")).replace('"', '\\"')
    cmd = (f". /etc/default/rasdaman; curl --user $RASCURL \"https://datacubes.earthmaps.io/rasdaman/admin/layer/"
           f"style/add?COVERAGEID={cov}&STYLEID={cov}_{band}&ABSTRACT={quote(abstract, safe='')}"
           f"&WCPSQUERYFRAGMENT={quote(wcps, safe='')}&COLORTABLETYPE=ColorMap&\" --data-urlencode "
           f"\"COLORTABLEDEFINITION={cmap}\"")
    return {"description": f"Create {NAMES[band]} class style", "when": "after_import", "cmd": cmd,
            "abort_on_error": True}


def build_recipe(cov, server_path, meta):
    ntile = TILE * TILE * len(BANDS)
    return {
        "config": {"service_url": "https://localhost/rasdaman/ows", "tmp_directory": "/tmp/", "blocking": True,
                   "mock": False, "automated": True, "track_files": False},
        "input": {"coverage_id": cov, "paths": [server_path]},
        "recipe": {
            "name": "general_coverage",
            "options": {
                "wms_import": True,
                "import_order": "ascending",
                # netCDF dims are (y, x): gridOrder Y = 0, X = 1; the bracket is in gridOrder order
                "tiling": f"ALIGNED [0:{TILE - 1}, 0:{TILE - 1}] tile size {ntile}",
                "coverage": {
                    "crs": "EPSG/0/3338",
                    "metadata": {"type": "xml", "global": recipe_metadata(meta)},
                    "slicer": {
                        "type": "netcdf",
                        "pixelIsPoint": True,
                        "bands": [{"name": b, "identifier": b, "nilValue": str(NODATA)} for b in BANDS],
                        "axes": {
                            "X": {"min": "${netcdf:variable:x:min}", "max": "${netcdf:variable:x:max}",
                                  "resolution": "${netcdf:variable:x:resolution}", "gridOrder": 1},
                            "Y": {"min": "${netcdf:variable:y:min}", "max": "${netcdf:variable:y:max}",
                                  "resolution": "${netcdf:variable:y:resolution}", "gridOrder": 0},
                        },
                    },
                },
            },
        },
        "hooks": [style_hook(cov, b) for b in BANDS],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--coverage-id", default=DEFAULT_ID)
    ap.add_argument("--out", help="output dir (default <data>/coverage/<id>/exported_<UTC export time>)")
    ap.add_argument("--server-dir", default="/opt/rasdaman-storage/coverage_data/environmental_hazard_index",
                    help="where the .nc will sit on the Rasdaman server (for the recipe's input path)")
    ap.add_argument("--force", action="store_true", help="write outputs even if a check against the PDF fails")
    a = ap.parse_args()

    info = read_pdf.read(a.pdf)
    rec, printed = info["record"], info["printed"]
    errs = check_record(rec)
    if errs:
        sys.exit("The PDF's decision record doesn't fit the repo:\n  " + "\n  ".join(errs))

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = "exported_" + (rec.get("exported") or built)[:16].replace(":", "") + "Z"  # e.g. exported_2026-11-11T0008Z (UTC)
    out = Path(a.out) if a.out else C.DATA / "coverage" / a.coverage_id / stamp
    out.mkdir(parents=True, exist_ok=True)

    land, reg = K.land_mask(), K.regions()
    cls, fpd = {}, {}
    for k in K.KEYS:
        vid = rec[k]["variant"]
        b = rec[k]["breaks"][vid]
        cls[k] = K.classes(k, vid, b, land)
        fpd[k] = int((K.full_precision_classes(k, vid, b, land) != cls[k]).sum())
    haz = K.hazard(cls, rec["hazard"], land)

    lines, bad = check_against_pdf(cls, haz, rec, printed, reg)
    lines.append(f"info cells whose class differs without the app's value encoding (full precision): {fpd}")
    report = "\n".join(lines)
    print(report)
    if bad and not a.force:
        sys.exit(f"{bad} check(s) against the PDF failed: nothing written (use --force to write anyway)")

    arrays = {k: np.where(cls[k] <= 2, cls[k], NODATA).astype(np.uint8) for k in K.KEYS}
    arrays["hazard"] = np.where(haz <= 2, haz, NODATA).astype(np.uint8)
    meta = build_metadata(a.coverage_id, rec, info, built)
    nc = out / f"{a.coverage_id}.nc"
    write_nc(nc, arrays, meta)
    recipe = build_recipe(a.coverage_id, f"{a.server_dir}/{nc.name}", meta)
    (out / "ingest.json").write_text(json.dumps(recipe, indent=2) + "\n")
    (out / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    (out / "decisions.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    (out / "build_checks.txt").write_text(f"{built} {a.pdf}\n{report}\n")
    if Path(a.pdf).resolve() != (out / info["file"]).resolve():
        shutil.copy2(a.pdf, out / info["file"])
    repo_ingest = HERE / "ingest"
    repo_ingest.mkdir(exist_ok=True)
    (repo_ingest / "ingest.json").write_text(json.dumps(recipe, indent=2) + "\n")
    for k in BANDS:
        u, n = np.unique(arrays[k], return_counts=True)
        print(f"{k:10s} " + ", ".join(f"{CLASS_NAMES[str(int(v))]} {c:,}" for v, c in zip(u, n)))
    print(f"wrote {out}/ ({nc.name} {nc.stat().st_size / 1e6:.2f} MB, ingest.json, metadata.json, decisions.json, "
          f"build_checks.txt) and {repo_ingest / 'ingest.json'}")


if __name__ == "__main__":
    main()
