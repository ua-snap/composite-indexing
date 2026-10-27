"""Progress to thaw at 1 m: (T_future - T_base) / (0 - T_base) in %, for ground frozen at the start (T_base < 0);
100 % = crosses 0 degC. T_base = GIPL 2004-2015 (the climate years run on observed weather, after the 2001-2003
start-up), T_future = 2040-2069. Ground not frozen at the start is flagged (na): no permafrost to lose."""
import numpy as np

from common import data as D


def build():
    tb, tf = D.gipl_mean(range(2004, 2016)), D.gipl_mean(range(2040, 2070))
    with np.errstate(all="ignore"):
        values = np.where(tb < 0, 100 * (tf - tb) / -tb, np.nan).astype("float32")
    return dict(values=values, na=np.isfinite(tb) & (tb >= 0))
