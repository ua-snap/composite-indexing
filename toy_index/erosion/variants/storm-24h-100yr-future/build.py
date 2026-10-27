"""DOT 24 h, 100-yr precipitation, 2050-2079, mean of GFDL-CM3 and NCAR-CCSM4 (RCP 8.5), inches (Rasdaman)."""
from common import data as D


def build():
    return dict(values=D.dot_rasdaman())
