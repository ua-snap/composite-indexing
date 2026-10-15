"""Paths, grids and study-area constants shared by all scripts."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path("/import/beegfs/CMIP6/jdpaul3/composite-indexing-data")
CRS = "EPSG:3338"

# Read-only inputs
ESA_AK = Path("/import/beegfs/CMIP6/jdpaul3/esa-cci/alaska")
ESA_RAW = Path("/import/beegfs/CMIP6/jdpaul3/esa-cci/raw/permafrost")
PISR_DATA = Path("/beegfs/CMIP6/jdpaul3/ArcticDEM-PISR_data")
TII_TIF = PISR_DATA / "pisr/terrain_insolation_index_32m_3338.tif"
WATER_TIF = PISR_DATA / "dem/arcticdem_v4.1_32m_water_3338.tif"

# Thaw orientation of the TII (ArcticDEM-PISR D22)
THAW_T0, THAW_T1 = 0.1, 1.4

# Rasdaman grids (EPSG:3338), from DescribeCoverage: envelope = cell edges.
# GIPL 1 km: X edges -979,791.709 .. 1,491,208.291 (2471), Y edges 434,479.751 .. 2,375,479.751 (1941)
GIPL_X0, GIPL_Y0, GIPL_RES = -979_791.709, 434_479.751, 1000.0
GIPL_NX, GIPL_NY = 2471, 1941
# tas 2 km: X edges -2,173,223.206 .. 4,262,776.794 (3218), Y edges 176,412.933 .. 2,548,412.933 (1186)
TAS_X0, TAS_Y0, TAS_RES = -2_173_223.206087799, 176_412.93264414696, 2000.0
TAS_NX, TAS_NY = 3218, 1186

# TII sample areas from ArcticDEM-PISR (label, lon, lat); 60 km boxes, north to south
REGIONS = [
    ("brooks", "Brooks Range", -150.6, 68.1),
    ("fairbanks", "Fairbanks", -147.72, 64.84),
    ("denali", "Denali", -151.0, 63.07),
]
REGION_HALF = 30_000  # m
WINDOW = 10_000  # pilot window side, m (D4)
