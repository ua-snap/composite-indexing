"""Change in the 1-hour, 100-year storm x model agreement on direction: mean(g, n) x agreement, g and n = each
model's % change from NOAA Atlas 14 to 2050-2079 (GFDL-CM3, NCAR-CCSM4); agreement = 1 when both models change in the
same direction (both up, or both down: an agreed decrease stays negative), 0.5 when they disagree. (A magnitude-based
weight, mean x (1 - |g-n|/(|g|+|n|)) = the smaller change, was tried first and dropped: CCSM4 is nearly always the
smaller, so it just followed CCSM4, rank corr 0.83-0.91.)"""
import numpy as np

from common import data as D


def build():
    g, n = D.dot_change_models("60m", 100)
    agree = np.where((g > 0) == (n > 0), 1.0, 0.5)
    v = (g + n) / 2 * agree
    v[~(np.isfinite(g) & np.isfinite(n))] = np.nan
    return dict(values=v.astype("float32"))
