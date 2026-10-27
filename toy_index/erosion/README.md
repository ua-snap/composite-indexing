# Erosion index

**Question:** which number best says "this place's hazard from heavy rain is low / medium / high (or rising)"?

## Variants
| id | What it is | Status |
|---|---|---|
| `storm-24h-100yr-future` | rain in the 24-hour, 100-year storm, 2050–2079 (mean of GFDL-CM3 and NCAR-CCSM4, RCP 8.5) | candidate |
| `storm-24h-100yr-change` | % change in that storm from NOAA Atlas 14 to 2050–2079 | candidate |

SNAP's DOT amounts are Atlas 14 × the climate model's change since 1979–2005 (Bieniek et al. 2022), so the change
variant is the model's projected change.

## Open questions
- Storm length and return interval: we picked 24 h / 100 yr out of 15 × 9 ([DATA_ISSUES](../DATA_ISSUES.md) #13).
  The local SNAP netCDFs hold every combination, so new variants need no server requests.
- Only RCP 8.5 and 2 models exist (#1, #2). Era 2050–2079 vs the others' 2040–2069 (#3).
- Rain alone isn't erosion: slope, soils, permafrost and vegetation matter (later variants).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py erosion` and `python -I toy_index/app/build_app.py`.
