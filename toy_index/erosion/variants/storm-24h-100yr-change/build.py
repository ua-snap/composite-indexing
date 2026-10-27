"""% change in the 24 h, 100-yr storm: DOT 2050-2079 vs NOAA Atlas 14. DOT = Atlas 14 x the WRF model's change since
1979-2005 (Bieniek et al. 2022), so this ratio is the model's projected change (checked: the ratio has under half the
< 20 km detail of either map)."""
from common import data as D


def build():
    return dict(values=D.pct(D.dot_rasdaman(), D.atlas14()))
