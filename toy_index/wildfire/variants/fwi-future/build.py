"""Mean daily Canadian Fire Weather Index (FWI), April-October 2040-2069, mean of 4 CMIP6 models, SSP5-8.5 (SNAP's
CMIP6 fire weather data release, summarized by scripts/01_data/summarize_fwi.py); ~25 km cells, bilinear to 1 km.
Outside the release's boreal domain the cell is flagged (na) and counts as Low."""
from common import data as D


def build():
    values, na = D.fwi("season_mean")
    return dict(values=values, na=na)
