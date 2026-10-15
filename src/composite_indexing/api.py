"""Cached earthmaps.io point fetcher (fallback + encoding spot-checks). Same politeness rules as rasdaman.py."""
import hashlib
import json
import time

import requests

from . import config as C
from .rasdaman import _log, MIN_GAP

BASE = "https://earthmaps.io"
CACHE = C.DATA / "api_cache"
_last = 0.0


def get_json(route, label=""):
    """route like '/temperature/64.8/-147.7'. Returns parsed JSON, fetched once and cached."""
    global _last
    CACHE.mkdir(parents=True, exist_ok=True)
    url = BASE + route
    path = CACHE / f"{label}_{hashlib.sha1(url.encode()).hexdigest()[:10]}.json"
    if path.exists():
        return json.loads(path.read_text())
    wait = MIN_GAP - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    t0 = time.monotonic()
    r = requests.get(url, timeout=60)
    _last = time.monotonic()
    _log(dict(utc=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), coverage="api", label=label,
              status=r.status_code, bytes=len(r.content), seconds=round(_last - t0, 2),
              file=path.name if r.ok else "", url=url))
    r.raise_for_status()
    path.write_text(r.text)
    return r.json()
