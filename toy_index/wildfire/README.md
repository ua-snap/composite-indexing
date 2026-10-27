# Wildfire index

**Question:** which number best says "this place's wildfire hazard is low / medium / high (or rising)"?

## Variants
| id | What it is | Status |
|---|---|---|
| `flam-future` | ALFRESCO relative flammability, 2040–2069 (5-model average, RCP 4.5) | candidate |
| `flam-change` | change in flammability from the 1980–2008 historical run to 2040–2069 | candidate |

Both take the point value from the SNAP API's watershed (HUC-12) average; the maps show 1 km pixels.

## Open questions
- Pixels vs watershed averages: SNAP says single ALFRESCO pixels aren't meaningful ([DATA_ISSUES](../DATA_ISSUES.md) #7).
  Variant idea: smooth the map to watershed or 10 km averages.
- "No value" vs zero: 26 % of land is exactly 0 (#9); a third of burnable land doesn't change at all.
- Which fire-management version Rasdaman serves (#13, #18).
- The historical run is driven by observed weather, the future by models (#18).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py wildfire` and `python -I toy_index/app/build_app.py`.
