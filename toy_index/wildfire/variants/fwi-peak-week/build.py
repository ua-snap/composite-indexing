"""Peak week of fire weather, 2040-2069: per model, the highest 7-day centred rolling mean of the mean daily FWI
curve (April-October; SNAP API op=7_day_rolling_average, "mean"), then the mean of 4 CMIP6 models, SSP5-8.5 (SNAP's
CMIP6 fire weather data release, summarized by scripts/01_data/summarize_fwi.py); ~25 km cells, bilinear to 1 km.
Outside the release's boreal domain the cell is flagged (na) and counts as Low."""
from common import data as D


def build():
    values, na = D.fwi("peak_week")
    return dict(values=values, na=na)
