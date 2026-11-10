"""Days per summer (June-August) 2040-2069 with High, Very High or Extreme fire danger (FWI >= 18; Alaska Fire Danger
Operating Plan ratings, as SNAP API op=summer_fire_danger_rating_days), mean of 4 CMIP6 models, SSP5-8.5 (SNAP's
CMIP6 fire weather data release, summarized by scripts/01_data/summarize_fwi.py); ~25 km cells, bilinear to 1 km.
Outside the release's boreal domain the cell is flagged (na) and counts as Low."""
from common import data as D


def build():
    values, na = D.fwi("high_days")
    return dict(values=values, na=na)
