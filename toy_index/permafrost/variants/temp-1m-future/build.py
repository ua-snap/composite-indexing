"""GIPL magt1m, 5ModelAvg RCP 4.5, mean of climate years 2040-2069; stuck cells and their 2 km border masked.
Only inside the ESA permafrost zone (PFR 2023 > 0); outside it the cell is flagged (na) and counts as Low."""
import numpy as np

from common import data as D
from common import grid as G


def build():
    gate = D.esa_gate()
    values = np.where(gate, D.gipl_mean(range(2040, 2070)), np.nan).astype("float32")
    return dict(values=values, na=G.land() & ~gate)
