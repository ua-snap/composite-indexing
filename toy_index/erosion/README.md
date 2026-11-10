# Erosion index

**Question:** which number best says "this place's hazard from heavy rain is low / medium / high (or rising)"?

## Variants (since 2026-11-09: 100-year storm, change only)
| Letter | id | What it is |
|---|---|---|
| A | `storm-1h-100yr-change` | % change, 1-hour, 100-year storm (short bursts) |
| B | `storm-24h-100yr-change` | % change, 24-hour, 100-year storm (repo starting point) |
| C | `storm-3d-100yr-change` | % change, 3-day, 100-year storm (multi-day rain) |
| D | `storm-1h-100yr-agreed` | A × model agreement on direction |
| E | `storm-24h-100yr-agreed` | B × model agreement on direction |
| F | `storm-3d-100yr-agreed` | C × model agreement on direction |

**Model agreement** (D–F): average change × agreement, where agreement = 1 when both models change in the same
direction (both up, or both down: an agreed decrease stays negative) and 0.5 when they disagree (2026-11-09; first
version set agreed decreases to 0; classes identical, since both-down is ≤ 1 % of land and already Low). A magnitude-based weight (average × (1 − |g − n| ÷ (|g| + |n|)), which equals the
smaller change) was tried first and dropped: NCAR-CCSM4 is nearly always the smaller, so it simply followed CCSM4
(rank corr 0.83–0.91 vs 0.23–0.32 with GFDL-CM3). Direction-only draws on both about equally (≈ 0.7 each) but is a
modest correction: same class as its plain-change variant on 84–88 % of land; 90–95 % of its High cells were already
High.

Retired 2026-11-09: `storm-24h-100yr-future` (depth: a map of where it is always wet), `storm-24h-10yr-change`,
`storm-24h-2yr-change` (team keeps the 100-year storm only). Reasons in each `variant.json`.

The change variants use the local SNAP netCDFs (`common/data.dot_local`, identical to the Rasdaman pull for 24 h /
100 yr) and the matching NOAA Atlas 14 annual-maximum grid (`common/data.atlas14(duration, interval)`, files in
`<data>/noaa_atlas14/ak/`; SNAP's pipeline multiplies the `_ams` grids: github.com/ua-snap/precip-dot,
`download_noaa_atlas14_data.py`). Any other storm needs one more small Atlas 14 download (3–7 MB).

**Findings (2026-11-09, 2050–2079):**
- Median change: 1 h +59 %, 3 d +47 %, 24 h/100 yr +42 %, 24 h/10 yr +32 %, 24 h/2 yr +34 %. Short bursts grow most.
- Every change variant puts the South mostly Low (wet places change least in %), the opposite of Variant A.
- The two models agree on the *direction* more often for frequent storms (sign differs on 23 % of land for 24 h /
  100 yr, 18 % for 1 h and 3 d, 7 % for 10 yr, 1 % for 2 yr) but **not on where change is largest**: rank
  correlation GFDL-CM3 vs NCAR-CCSM4 is −0.08 to +0.14 for every storm. GFDL-CM3 projects about twice the change
  (median +59 % vs +22 % for 24 h / 100 yr) and a wider spread, so the averaged map follows GFDL-CM3 (rank corr 0.84
  vs 0.52). The *pattern* of any change map is therefore one model's pattern, not a robust signal.
- Variants agree with each other only partly: B with E 68 % same class (rho 0.83), B with D 63 % (0.76); C (1 h) and
  F (2 yr) stand apart (rho 0.24–0.33 with the others).

## Open questions
- Given the model disagreement on *where*, should the erosion index use change at all, or a model-agreement measure
  (both models increase by more than X %), or the depth (Variant A) with change as context?
- Storm length and return interval: we picked 24 h / 100 yr out of 15 × 9 ([DATA_ISSUES](../DATA_ISSUES.md) #13).
  The local SNAP netCDFs hold every combination, so new variants need no server requests.
- Only RCP 8.5 and 2 models exist (#1, #2). Era 2050–2079 vs the others' 2040–2069 (#3).
- Rain alone isn't erosion: slope, soils, permafrost and vegetation matter (later variants).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py erosion` and `python -I toy_index/app/build_app.py`.
