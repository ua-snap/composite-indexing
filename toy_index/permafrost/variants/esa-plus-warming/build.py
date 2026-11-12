"""Projected ground-surface temperature inside the ESA permafrost zone, by the delta change method (D25, PTI V2):
ESA CCI GST 2014-2023 (observed level) + GIPL magtsurface warming 2014-2023 -> 2040-2069 (5-model average, RCP 4.5).
GIPL contributes only its change; the level is ESA's. Gate: ESA permafrost zone (common/data.esa_gate); outside it the class is Low.
Why not the PTI two-way table: at 2040-2069 RCP 4.5, 88 % of gated cells warm < 2 degC (the table's first column), so
the table collapses to today's level alone (Arctic Low, the rest Medium, 0.6 % High)."""
import numpy as np
from common import data as D
from common import grid as G


def build():
    gate, today = D.esa_gate(), D.esa_gst_today()
    d = D.gipl_mean(range(2040, 2070), "magtsurface") - D.gipl_mean(range(2014, 2024), "magtsurface")
    values = np.where(gate, today + d, np.nan).astype("float32")
    return dict(values=values, na=G.land() & ~gate)
