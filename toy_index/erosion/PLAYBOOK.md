# Erosion playbook

**Short answer:** today's erosion index is rain alone: the 24-hour, 100-year storm. Next we test which storm matters
(short bursts vs multi-day rain, rare vs frequent storms), whether the two climate models even agree on the
direction of change, and whether adding ground that erodes easily (slope, soils, cover) changes the picture. Every
storm variant comes from local SNAP files, so the first session needs no server requests.

**Key terms**
- **Precipitation frequency:** the rain depth of a storm of a given length (1 hour to 60 days) expected once per
  return interval (2 to 1000 years). Engineers size culverts and drains with it.
- **NOAA Atlas 14:** the official US precipitation frequency estimates from rain gauges. SNAP's DOT values are Atlas
  14 × each climate model's change since 1979–2005 (Bieniek et al. 2022).
- **RUSLE:** the standard soil-loss equation: rain (R) × soil erodibility (K) × slope length and steepness (LS) ×
  cover (C).

Catalog IDs in brackets (C6, H4, ...) refer to the Arctic-EDS Candidate Data Catalog. It has no erosion topic of its
own: erosion appears under Hydrology (with flooding, ice breakup, water supply, river navigation) and under Permafrost
(thermokarst, thaw). Today's DOT data is [C6].

## 1. Decide first: what does "High erosion hazard" mean here?
- **Heavy rain washing out roads, culverts and slopes** (rain-driven, what DOT data was built for), **ground that
  erodes easily** (rain × terrain × soil), **thermo-erosion** (thawing ground; overlaps the permafrost index), or
  **coastal erosion** (a separate hazard; different data)?
- The answer decides whether rain alone is enough or terrain and soil come in.

## 2. Where we start
`storm-24h-100yr-future` (2050–2079 inches) and `storm-24h-100yr-change` (% change from Atlas 14). Both average two
models (GFDL-CM3, NCAR-CCSM4) under RCP 8.5, the only scenario in the dataset.

## 3. Variant backlog
Priority 1 = local data, no requests · 2 = more work or a metadata check · 3 = new data or a different hazard.

| Proposed id | Idea | Data | Cost | Priority |
|---|---|---|---|---|
| `storm-1h-100yr-change` | short, intense bursts (convective; the paper finds these grow fastest) | local DOT netCDFs | local | 1 |
| `storm-3d-100yr-change` | multi-day rain (saturated slopes) | local DOT | local | 1 |
| `storm-24h-10yr-change` | frequent storms (wear on roads every few years) | local DOT | local | 1 |
| `storm-models-agree` | do both models project an increase? (they disagree at Fort Wainwright: +43 % vs −11 %) | local DOT | local | 1 |
| `storm-24h-100yr-upper` | 90 % upper confidence bound (precautionary) | local DOT `pf_upper` | local | 1 |
| `storm-late-century-change` | 2080–2099 | local DOT | local | 1 |
| `storm-multi-duration` | mean % change across 1 h, 24 h, 3 d | local DOT | local | 2 |
| `rusle-lite` | rain × soil erodibility × slope × cover, relative 0–1 | DOT + STATSGO2 K factor (local) + slope from ArcticDEM 32 m (read-only) + NLCD (local) | local, a day's work | 2 |
| `wet-days-change` | change in wet days per year (how often it rains, not how hard) | [C13] Rasdaman `wet_days_per_year` (20 km) | metadata check, then requests | 2 |
| `streamflow-change` | change in high flows along streams (bank erosion, washouts) | [H2] CMIP6 Arctic stream flow (stream lines; not SE Alaska) | lines, not a grid: needs design | 2 |
| `idf-cmip6` | the same storms from newer CMIP6 downscaling (also rain on snow) | [H4] NG-IDF (Alaska "TBD" in the catalog; Rasdaman has `NG_IDF_CESM_WRF`) | check Alaska coverage first | 3 |
| `storm-cmip6-wrf` | storms from the new CMIP6 dynamical downscaling (could replace DOT's 2 CMIP5 models) | [C19] Bieniek, in progress | when available | 3 |
| `coastal` | shoreline loss and sea-level exposure | [S1] EPA sea level rise (30 m), [S2] storm surge (2.5 km); not SNAP | new download, separate hazard | 3 |

## 4. How we'll compare variants
- **Standard comparison** (`compare.py`): maps, distributions, class shares by region, class agreement, preset places.
- **Model spread:** every change variant also reported per model; where the models disagree in sign, the variant
  is shaky there.
- **Reality check:** recent observed extremes ([C1] WRF-downscaled ERA5, 1960–2023 hourly; Rasdaman
  `era5_4km_daily_rainnc_sum`, metadata check) against Atlas 14: are big storms already more common?

## 5. Decisions for the team
1. Meaning of "High" (section 1).
2. Which storm (length, return interval): the DOT design standard, or what damages things in practice?
3. RCP 8.5 only and 2 models (DATA_ISSUES #1, #2): acceptable for a mid-century, middle-emissions index?
4. Rain only, or rain × terrain (`rusle-lite`)?
5. Is this really a "heavy rain" index, with flooding [H1, H2] and coastal hazards [S1, S2] as separate indices later?

## 6. First session
1. Build the six priority-1 variants (local, mostly loops over `common/data.dot_local`).
2. Publish; look at where 1 h and 3 d changes disagree and where the models disagree.
3. Check STATSGO2 has usable K factors for Alaska before committing to `rusle-lite`.
