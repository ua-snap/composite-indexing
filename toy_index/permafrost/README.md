# Permafrost index

**Question:** which number best says "this place's permafrost thaw hazard is low / medium / high (or rising)"?

## Variants
| id | What it is | Status |
|---|---|---|
| `temp-1m-future` | GIPL ground temperature at 1 m, 2040–2069 (5-model average, RCP 4.5) | candidate |
| `thaw-progress` | warming at 1 m from 2004–2015 to 2040–2069 as a % of the distance to 0 °C (100 % = crosses 0 °C); ground not frozen at the start counts as Low | candidate |

Both mask GIPL's stuck cells and a 2 km border around them (decision D17).

## Open questions
- What "High" means: ground above 0 °C may mean nothing left to thaw ([DATA_ISSUES](../DATA_ISSUES.md) #10).
  `thaw-progress` is one answer; the team should confirm.
- Bring in the Permafrost Thaw Index work (`docs/PTI.md`, `docs/PTI_COMPOSITE.md`) as variants: PTI classes are already
  on the GIPL grid (`<data>/results/t4/index_variants.nc`).
- The 2004–2015 baseline is short (the only GIPL years run on observed weather) (#16).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py permafrost` and `python -I toy_index/app/build_app.py`.
