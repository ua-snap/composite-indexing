# Permafrost index

**Question:** which number best says "this place's permafrost thaw hazard is low / medium / high (or rising)"?

## Variants
| id | What it is | Status |
|---|---|---|
| `temp-1m-future` | GIPL ground temperature at 1 m, 2040–2069 (5-model average, RCP 4.5); ESA permafrost zone only, outside = Low (since 2026-11-09) | candidate |
| `thaw-progress` | warming at 1 m from 2004–2015 to 2040–2069 as a % of the distance to 0 °C (100 % = crosses 0 °C); ESA permafrost zone only; outside it, or not frozen at the start, counts as Low | candidate |
| `esa-plus-warming` | ground-surface temperature at 2040–2069 = ESA's observed level 2014–2023 + GIPL's surface warming (delta change method, as PTI V2); outside the ESA zone = Low. **Variant C** (was D until `surface-warming` was retired) | candidate (2026-11-09) |

All mask GIPL's stuck cells and a 2 km border around them (decision D17), and all are gated by the ESA permafrost
zone (PFR 2023 > 0, `common/data.esa_gate`). All GIPL reads go through `common/data.gipl_mean` →
`C.gipl_file_year` (labels 20 years late; checked 2026-11-09: A = mean of files 2060–2089 to 1e-6 °C).

Retired: `surface-warming` (ground-surface warming only, briefly Variant C, 2026-11-09). It put the Arctic High
(73 % of Arctic land) and the Interior, West and South Low: Arctic amplification makes the surface warm most where
permafrost is coldest, which is not where it thaws first (the Interior and Seward Peninsula are). Reason in its
`variant.json` ("retired").

## Open questions
- Why `esa-plus-warming` (C) is not the PTI two-way table: at 2040–2069 RCP 4.5, 88 % of gated cells warm < 2 °C (the table's first
  column), so the table collapses to today's level alone (Arctic Low, the rest Medium, 0.6 % High). In D, today's
  level spreads over ~8 °C and warming over ~1 °C, so C mostly ranks by today's level.
- `esa-plus-warming` breaks are thirds placeholders (−1.0 / 2.1 °C). Anchor High at the field-site surface split
  (+1.7 to +2.3 °C, GIPL_ISSUE_2)?
- Bring in the Permafrost Thaw Index work (`docs/PTI.md`, `docs/PTI_COMPOSITE.md`) as variants: PTI classes are already
  on the GIPL grid (`<data>/results/t4/index_variants.nc`).
- The 2004–2015 baseline is short (the only GIPL years run on observed weather) (#16).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py permafrost` and `python -I toy_index/app/build_app.py`.
