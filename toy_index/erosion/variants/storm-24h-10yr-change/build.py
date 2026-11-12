"""% change in the 24-hour, 10-year storm: 100 x (DOT 2050-2079 / NOAA Atlas 14 - 1), DOT = mean of GFDL-CM3 and NCAR-CCSM4
(local SNAP netCDFs, RCP 8.5), Atlas 14 = annual maximum series ak10yr24ha_ams. Same recipe as storm-24h-100yr-change."""
from common import data as D


def build():
    return dict(values=D.pct(D.dot_local("2050-2079", "24h", 10.0), D.atlas14("24h", 10)))
