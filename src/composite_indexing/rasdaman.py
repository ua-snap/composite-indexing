"""Polite, cached WCS 2.0.1 GetCoverage client for SNAP's Rasdaman (Zeus).

Rules (CLAUDE.md): small bbox subsets only, sequential, >= MIN_GAP s between requests, every response cached on disk
and never re-requested. Every request (and cache hit) is logged to <data>/rasdaman_cache/requests.csv.
"""
import csv
import hashlib
import time
from datetime import datetime, timezone
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


def get_coverage(coverage, subsets, fields=None, label="", fmt="application/netcdf", timeout=180):
    """Return the cached file path for this request, fetching it once if needed."""
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
