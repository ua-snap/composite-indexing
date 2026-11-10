# Erosion index

**Question:** which number best says "this place's hazard from heavy rain is low / medium / high (or rising)"?

## Variants (since 2026-11-10: change only; 100-year and 10-year storms, 1 h / 24 h / 3 d)
| Letter | id | What it is |
|---|---|---|
| A | `storm-1h-100yr-change` | % change, 1-hour, 100-year storm (short bursts) |
| B | `storm-24h-100yr-change` | % change, 24-hour, 100-year storm (repo starting point) |
| C | `storm-3d-100yr-change` | % change, 3-day, 100-year storm (multi-day rain) |
| D | `storm-1h-10yr-change` | % change, 1-hour, 10-year storm |
| E | `storm-24h-10yr-change` | % change, 24-hour, 10-year storm (retired 2026-11-09, back 2026-11-10) |
| F | `storm-3d-10yr-change` | % change, 3-day, 10-year storm |

All are the two-model average. Where the models disagree on direction (18–23 % of land for the 100-year storm,
3–7 % for the 10-year) the average mixes an increase with a decrease; the team accepts this (con on A–C).

Retired 2026-11-10: `storm-{1h,24h,3d}-100yr-agreed` (the old D–F: change × model agreement on direction, 1 if both
models change the same way, 0.5 if not). Feedback: the multiplier is not intuitive. It was also a modest correction
(same class as plain change on 84–88 % of land). A magnitude-based weight was tried before it and dropped (it just
followed NCAR-CCSM4).

Retired 2026-11-09: `storm-24h-100yr-future` (depth: a map of where it is always wet), `storm-24h-2yr-change`.
Reasons in each `variant.json`.

The change variants use the local SNAP netCDFs (`common/data.dot_local`, identical to the Rasdaman pull for 24 h /
100 yr) and the matching NOAA Atlas 14 annual-maximum grid (`common/data.atlas14(duration, interval)`, files in
`<data>/noaa_atlas14/ak/`; SNAP's pipeline multiplies the `_ams` grids: github.com/ua-snap/precip-dot,
`download_noaa_atlas14_data.py`). Any other storm needs one more small Atlas 14 download (3–7 MB; 10-year 1 h and 3 d grids added 2026-11-10).

**Findings (2026-11-09, 2050–2079):**
- Median change: 1 h +59 %, 3 d +47 %, 24 h/100 yr +42 %, 24 h/10 yr +32 %, 24 h/2 yr +34 %. Short bursts grow most.
- Every change variant puts the South mostly Low (wet places change least in %), the opposite of Variant A.
- The two models agree on the *direction* more often for frequent storms (sign differs on 23 % of land for 24 h /
  100 yr, 18 % for 1 h and 3 d, 7 % for 10 yr, 1 % for 2 yr) but **not on where change is largest**: rank
  correlation GFDL-CM3 vs NCAR-CCSM4 is −0.08 to +0.14 for every storm. GFDL-CM3 projects about twice the change
  (median +59 % vs +22 % for 24 h / 100 yr) and a wider spread, so the averaged map follows GFDL-CM3 (rank corr 0.84
  vs 0.52). The *pattern* of any change map is therefore one model's pattern, not a robust signal.
- Variants agree with each other only partly (letters as of 2026-11-09): 24 h/100 yr with 24 h/10 yr 68 % same
  class (rho 0.83); the 2-year storm stood apart (rho 0.24–0.33 with the others).
- 10-year storms (2026-11-10): median 1 h +43 %, 24 h +32 %, 3 d +31 %. Both models increase on 93–97 % of land,
  but rank correlation between them is still near 0 (−0.05 to 0.21). Each is the same class as its 100-year partner
  on 66–69 % of land (rho 0.79–0.83). Thirds: D 37/50 %, E 27/37 %, F 26/37 %.

## Open questions
- Given the model disagreement on *where*, should the erosion index use change at all? (Agreement weighting was
  tried and dropped 2026-11-10; depth was retired 2026-11-09.)
- 100-year or 10-year storm? Both models agree on direction far more for the 10-year storm, but change is smaller
  and the boundaries closer together.
- Storm length and return interval: we picked 24 h / 100 yr out of 15 × 9 ([DATA_ISSUES](../DATA_ISSUES.md) #13).
  The local SNAP netCDFs hold every combination, so new variants need no server requests.
- Only RCP 8.5 and 2 models exist (#1, #2). Era 2050–2079 vs the others' 2040–2069 (#3).
- Rain alone isn't erosion: slope, soils, permafrost and vegetation matter (later variants).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py erosion` and `python -I toy_index/app/build_app.py`.
