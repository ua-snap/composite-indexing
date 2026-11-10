"""Ground-surface warming inside the ESA permafrost zone: GIPL magtsurface 2040-2069 minus 2014-2023 (degC; 5-model
average, RCP 4.5; same "today" as PTI V2, D35). No 0 degC threshold anywhere: the class comes from the warming alone.
Gate = ESA CCI permafrost fraction 2023 > 0 (the PTI gate, D12/D26). Outside it (PFR 0, or no ESA value: 85 % of
those are in the South and GIPL also shows no permafrost there) the cell is flagged (na): no permafrost to thaw, Low.
Inside it, GIPL stuck cells + 2 km border have no value (D17). Surface, not 1 m: at 1 m, thawing ground holds near
0 degC while its ice melts, so the warmest permafrost shows the least warming (median 0.6 degC at 1 m vs 1.6 at the
surface for cells starting between -1 and 0 degC)."""
import numpy as np
from common import data as D
from common import grid as G


def build():
    gate = D.esa_gate()
    d = D.gipl_mean(range(2040, 2070), "magtsurface") - D.gipl_mean(range(2014, 2024), "magtsurface")
    values = np.where(gate, d, np.nan).astype("float32")
    return dict(values=values, na=G.land() & ~gate)
