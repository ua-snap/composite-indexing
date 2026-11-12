"""% change in the 1-hour, 100-year storm: 100 x (DOT 2050-2079 / NOAA Atlas 14 - 1), DOT = mean of GFDL-CM3 and NCAR-CCSM4
(local SNAP netCDFs, RCP 8.5), Atlas 14 = annual maximum series ak100yr60ma_ams. Same recipe as storm-24h-100yr-change."""
from common import data as D


def build():
    return dict(values=D.pct(D.dot_local("2050-2079", "60m", 100.0), D.atlas14("60m", 100)))
