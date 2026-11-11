"""Polite, cached WCS 2.0.1 GetCoverage client for SNAP's Rasdaman (Zeus).

Rules (CLAUDE.md): small bbox subsets only, sequential, >= MIN_GAP s between requests, every response cached on disk
and never re-requested. Every request (and cache hit) is logged to <data>/rasdaman_cache/requests.csv.
"""
import csv
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

from . import config as C

URL = "https://zeus.snap.uaf.edu/rasdaman/ows"
CACHE = C.DATA / "rasdaman_cache"
LOG = CACHE / "requests.csv"
MIN_GAP = 1.5  # s between requests
_last = 0.0


def _subset(axis, lo, hi=None):
    if isinstance(lo, str):
        lo = f'"{lo}"'
        hi = f'"{hi}"' if hi is not None else None
    return f"{axis}({lo})" if hi is None else f"{axis}({lo},{hi})"


def build_url(coverage, subsets, fields=None, fmt="application/netcdf"):
    """subsets: list of (axis, lo) or (axis, lo, hi); strings are quoted (dates)."""
    params = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"), ("coverageId", coverage)]
    params += [("subset", _subset(*s)) for s in subsets]
    if fields:
        params.append(("rangesubset", ",".join(fields)))
    params.append(("format", fmt))
    return f"{URL}?{urlencode(params)}"


def _log(row):
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def get_coverage(coverage, subsets, fields=None, label="", fmt="application/netcdf", timeout=180, fetch=True):
    """Return the cached file path for this request, fetching it once if needed (fetch=False: cache only, else raise)."""
    global _last
    CACHE.mkdir(parents=True, exist_ok=True)
    url = build_url(coverage, subsets, fields, fmt)
    ext = {"application/netcdf": "nc", "image/tiff": "tif", "application/json": "json"}.get(fmt, "bin")
    path = CACHE / f"{coverage}_{label}_{hashlib.sha1(url.encode()).hexdigest()[:10]}.{ext}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if path.exists():
        _log(dict(utc=now, coverage=coverage, label=label, status="cache", bytes=path.stat().st_size, seconds=0,
                  file=path.name, url=url))
        return path
    if not fetch:
        raise FileNotFoundError(f"{coverage} {label}: not cached and fetch=False")
    wait = MIN_GAP - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    t0 = time.monotonic()
    r = requests.get(url, timeout=timeout)
    _last = time.monotonic()
    dt = round(_last - t0, 2)
    _log(dict(utc=now, coverage=coverage, label=label, status=r.status_code, bytes=len(r.content), seconds=dt,
              file=path.name if r.ok else "", url=url))
    if not r.ok or r.content[:5] in (b"<?xml", b"<ows:"):
        raise RuntimeError(f"{coverage} {label}: HTTP {r.status_code}\n{r.text[:1500]}")
    tmp = path.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.rename(path)
    return path


def _polite_get(method, **kw):
    """One request, >= MIN_GAP s after the previous one (shared with get_coverage)."""
    global _last
    wait = MIN_GAP - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    t0 = time.monotonic()
    r = requests.request(method, URL, timeout=kw.pop("timeout", 180), **kw)
    _last = time.monotonic()
    return r, round(_last - t0, 2)


def wcps(query, label, cache=True):
    """WCPS ProcessCoverages (POST) -> response text. Cached by query when the answer is data (cache=False for
    answers that should be re-read, e.g. after a re-ingest); server exceptions come back as text, uncached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"wcps_{label}_{hashlib.sha1(query.encode()).hexdigest()[:10]}.txt"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if cache and path.exists() and path.stat().st_size:
        _log(dict(utc=now, coverage="wcps", label=label, status="cache", bytes=path.stat().st_size, seconds=0,
                  file=path.name, url=query))
        return path.read_text()
    r, dt = _polite_get("POST", data=dict(service="WCS", version="2.0.1", request="ProcessCoverages", query=query))
    _log(dict(utc=now, coverage="wcps", label=label, status=r.status_code, bytes=len(r.content), seconds=dt,
              file=path.name, url=query))
    if cache and r.ok and r.content and not r.content.lstrip().startswith(b"<"):
        path.write_text(r.text)
    return r.text


def get_map(params, label, cache=True):
    """WMS GetMap (params without service/request) -> path of the cached PNG; raises with the server's text if the
    answer is not a PNG."""
    p = dict(service="WMS", version="1.3.0", request="GetMap", format="image/png", transparent="true", **params)
    url = f"{URL}?{urlencode(p)}"
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"wms_{label}_{hashlib.sha1(url.encode()).hexdigest()[:10]}.png"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if cache and path.exists() and path.stat().st_size:
        return path
    r, dt = _polite_get("GET", params=p)
    _log(dict(utc=now, coverage="wms", label=label, status=r.status_code, bytes=len(r.content), seconds=dt,
              file=path.name, url=url))
    if not r.content.startswith(b"\x89PNG"):
        raise RuntimeError(f"WMS {label}: HTTP {r.status_code}: {r.text[:1500]}")
    path.write_bytes(r.content)
    return path


def describe(coverage, out=None):
    """DescribeCoverage XML text (always fetched; saved to `out` if given)."""
    r, dt = _polite_get("GET", params=dict(service="WCS", version="2.0.1", request="DescribeCoverage",
                                           coverageId=coverage))
    _log(dict(utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), coverage=coverage, label="describe",
              status=r.status_code, bytes=len(r.content), seconds=dt, file=str(out or ""), url=r.url))
    if out:
        Path(out).write_text(r.text)
    return r.text
