"""Progress to thaw at 1 m: (T_future - T_base) / (0 - T_base) in %, for ground frozen at the start (T_base < 0);
100 % = crosses 0 degC. T_base = GIPL 2004-2015 (the climate years run on observed weather, after the 2001-2003
start-up), T_future = 2040-2069. Only inside the ESA permafrost zone (PFR 2023 > 0). Flagged (na, counts as Low):
outside the zone, or GIPL not frozen at the start (no permafrost to lose)."""
import numpy as np

from common import data as D
from common import grid as G


def build():
    gate = D.esa_gate()
    tb, tf = D.gipl_mean(range(2004, 2016)), D.gipl_mean(range(2040, 2070))
    frozen = gate & (tb < 0)
    with np.errstate(all="ignore"):
        values = np.where(frozen, 100 * (tf - tb) / -tb, np.nan).astype("float32")
    return dict(values=values, na=G.land() & (~gate | (np.isfinite(tb) & (tb >= 0))))
