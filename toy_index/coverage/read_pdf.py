"""Read the team workbench's "Download PDF" file: the decision record plus the numbers the PDF prints (for checks).

  python -I toy_index/coverage/read_pdf.py <file.pdf>        # prints what it found

The PDF is made in the browser by jsPDF (app_template.html, buildPdf): standard fonts, one text line per `(...) Tj`
in Flate-compressed page streams. No PDF library is needed (none is installed in the env): this reads the page
streams in page order and returns the text lines. What it returns (read(path) -> dict):

  record   the "Decision record (JSON, same shape as toy_index/composite/decisions.json)" block, parsed. Per index
           {variant, letter, breaks: {variant: [b1, b2]}, note, high, low, decided}; hazard = the rule parameters
           {rule, weights, avgCuts, prodCuts, countHigh, countMed, custom, missing, note, high, low, decided};
           exported (UTC ISO time), data_built (the app's data date).
  printed  numbers the PDF shows, used as test values: shares of land per index and for the hazard ("Share of land",
           "Result"), the hazard by region (% of land), the named-places table, the 27 rule combinations.
  sha256   of the file, for the coverage metadata.

Long JSON lines are wrapped by jsPDF at spaces (the space is dropped), so lines are joined with a space: exact for
all numbers and identifiers; free text keeps its words (characters outside Latin-1 were already "?" in the PDF).
"""
import hashlib
import json
import re
import sys
import zlib
from pathlib import Path

CLS = {"Low": 0, "Medium": 1, "High": 2, "L": 0, "M": 1, "H": 2}
KEYS = ["wildfire", "erosion", "permafrost"]
REGIONS = ["Arctic", "Interior", "West", "South"]

_ESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}


def _unescape(s):
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i:i + 1]
        if c == b"\\":
            nxt = s[i + 1:i + 2]
            m = re.match(rb"[0-7]{1,3}", s[i + 1:i + 4])
            if m:
                out.append(int(m.group(), 8) & 255)
                i += 1 + len(m.group())
                continue
            out += _ESC.get(nxt, nxt)
            i += 2
            continue
        out += c
        i += 1
    return out.decode("cp1252", errors="replace")


def _objects(b):
    return {int(n): body for n, body in re.findall(rb"(\d+) 0 obj(.*?)endobj", b, re.S)}


def _stream(body):
    m = re.search(rb"<<(.*?)>>\s*stream\r?\n(.*?)\r?\n?endstream", body, re.S)
    head, data = m.group(1), m.group(2)
    return zlib.decompress(data) if b"FlateDecode" in head else data


TEXT_OP = re.compile(rb"/(F\d+) ([\d.]+) Tf|\(((?:\\.|[^\\)])*)\)\s*Tj", re.S)


def lines(path):
    """[(page, font, text)] in drawing order, page footers dropped."""
    b = Path(path).read_bytes()
    objs = _objects(b)
    pages_obj = next(v for v in objs.values() if re.search(rb"/Type\s*/Pages\b", v))
    kids = [int(n) for n in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids\s*\[(.*?)\]", pages_obj, re.S).group(1))]
    out = []
    for p, k in enumerate(kids, 1):
        refs = re.search(rb"/Contents\s*(\[.*?\]|\d+ 0 R)", objs[k], re.S).group(1)
        font = None
        for c in [int(n) for n in re.findall(rb"(\d+) 0 R", refs)]:
            for m in TEXT_OP.finditer(_stream(objs[c])):
                if m.group(1):
                    font = m.group(1).decode()
                else:
                    t = _unescape(m.group(3))
                    if t.startswith("Environmental Hazard Index team workbench") or re.fullmatch(r"Page \d+ of \d+", t):
                        continue
                    out.append((p, font, t))
    return out


def _pct(s):
    s = s.strip()
    return 0.4 if s.startswith("<1") else float(s.replace("%", "").strip())  # "<1 %": just under 0.5


def _shares(s):
    """'Low 77 % · Medium 13 % · High 10 % · no value 5 %' -> [77, 13, 10, nv] (percent; nv 0 if not shown)."""
    d = dict(re.findall(r"(Low|Medium|High|no value) (<1 %|[\d.]+ %)", s))
    return [_pct(d[k]) if k in d else 0.0 for k in ("Low", "Medium", "High", "no value")]


def read(path):
    L = lines(path)
    texts = [t for _, _, t in L]
    prose = " ".join(texts)

    # decision record: the courier lines after its heading, to the end
    i = next(j for j, t in enumerate(texts) if t.startswith("Decision record (JSON"))
    rec_font = L[i + 1][1]
    block = [t for _, f, t in L[i + 1:] if f == rec_font]
    record = json.loads(" ".join(block))

    printed = {}
    # "Share of land: ..." once per index, in index order (page 2-3)
    sh = re.findall(r"Share of land: (.*?%)\.", prose)
    printed["index_shares"] = dict(zip(KEYS, map(_shares, sh)))
    printed["hazard_shares"] = _shares(re.search(r"Result: (.*?) of Alaska's land", prose).group(1))
    # 27 combinations: Wildfire, Erosion, Permafrost -> Hazard
    printed["combinations"] = {(CLS[a], CLS[b], CLS[c]): CLS[d]
                               for a, b, c, d in re.findall(r"\b([LMH])([LMH])([LMH])->([LMH])\b", prose)}
    # hazard by region (page 1): "Arctic" then Low, Medium, High percentages
    printed["hazard_regions"] = {}
    j = texts.index("By region (% of land)")
    for r in REGIONS:
        k = texts.index(r, j)
        printed["hazard_regions"][r] = [float(x) for x in texts[k + 1:k + 4]]
    # named places (page 1): name, then Wildfire, Erosion, Permafrost, Hazard chips
    printed["places"] = {}
    j = texts.index("At named places")
    k = texts.index("Hazard", j) + 1
    pg = L[k][0]
    while k + 4 < len(L) and L[k][0] == pg:
        name, chips = texts[k], texts[k + 1:k + 5]
        if not all(c in ("Low", "Medium", "High", "No value") for c in chips):
            break
        printed["places"][name] = [3 if c == "No value" else CLS[c] for c in chips]
        k += 5
    m = re.search(r"(\d) of 4 decisions made by the team", prose)
    printed["decided_count"] = int(m.group(1)) if m else None
    return dict(record=record, printed=printed, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                file=Path(path).name)


if __name__ == "__main__":
    r = read(sys.argv[1])
    print(json.dumps({k: v for k, v in r["record"].items()}, indent=1, ensure_ascii=False)[:3000])
    p = dict(r["printed"])
    p["combinations"] = {"".join("LMH"[i] for i in k): "LMH"[v] for k, v in p["combinations"].items()}
    print(json.dumps(p, indent=1))
    print("sha256", r["sha256"])
