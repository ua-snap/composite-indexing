"""Independent ground temperature observations for GIPL_ISSUE_2: UAF Permafrost Lab / GTN-P "Thermal State of
Permafrost in North America - continuously observed ground temperatures" (Arctic Data Center, one package per
June-May year, daily CSV per site + a sites roster). US sites only. Sequential, >= 1 s apart, cached: a file already
on disk is never requested again.
Output: <data>/boreholes/tsp_continuous/<package year>/<file>.csv; request log <data>/boreholes/requests.csv
"""
import csv
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from composite_indexing import config as C  # noqa: E402

ADC = "https://arcticdata.io/metacat/d1/mn/v2"
OUT = C.DATA / "boreholes"
PACKAGES = {  # June-May year: package DOI (continuously observed ground temperatures)
    "2015_2016": "doi:10.18739/A28911R1W", "2016_2017": "doi:10.18739/A24J09X6N",
    "2017_2018": "doi:10.18739/A2D795976", "2018_2019": "doi:10.18739/A2W37KW4J",
    "2019_2020": "doi:10.18739/A29G5GF47", "2020_2021": "doi:10.18739/A2F47GV9K",
    "2021_2022": "doi:10.18739/A2TD9N93H", "2022_2023": "doi:10.18739/A2513TX7M",
    "2023_2024": "doi:10.18739/A2K35MG41", "2024_2025": "doi:10.18739/A2F47GW72",
}
GAP = 1.0
_last = 0.0


def get(url, **kw):
    global _last
    wait = GAP - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    t0 = time.monotonic()
    r = requests.get(url, timeout=120, **kw)
    _last = time.monotonic()
    new = not (OUT / "requests.csv").exists()
    with open(OUT / "requests.csv", "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["utc", "status", "bytes", "seconds", "url"])
        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), r.status_code, len(r.content),
                    round(_last - t0, 2), r.url])
    r.raise_for_status()
    return r


def file_list(year, doi):
    path = OUT / "tsp_continuous" / year / "_files.json"
    if path.exists():
        return json.loads(path.read_text())
    key = doi.split("/")[-1]
    r = get(f"{ADC}/query/solr/", params=dict(q=f"resourceMap:*{key}*", fl="identifier,fileName,formatId,size",
                                              rows=1000, wt="json"))
    docs = [d for d in r.json()["response"]["docs"] if d.get("formatId") == "text/csv"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(docs, indent=1))
    return docs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for year, doi in PACKAGES.items():
        docs = file_list(year, doi)
        keep = [d for d in docs if d["fileName"].startswith("US_") or "roster" in d["fileName"].lower()]
        n_new = 0
        for d in keep:
            dest = OUT / "tsp_continuous" / year / d["fileName"]
            if dest.exists():
                continue
            dest.write_bytes(get(f"{ADC}/object/{d['identifier']}").content)
            n_new += 1
        print(year, doi, f"{len(keep)} files ({n_new} new)", flush=True)


if __name__ == "__main__":
    main()
