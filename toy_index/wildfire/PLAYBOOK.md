# Wildfire playbook

**Short answer:** today's wildfire index is one ALFRESCO number per 1 km pixel. Next we test three things: whether
area averages read better than pixels (SNAP's own advice), how much the answer depends on the climate model and
scenario, and whether fire *weather* (a separate CMIP6 product) tells the same story as simulated *burning*. The
first session needs no server requests.

**Key terms**
- **Relative flammability:** the share of ALFRESCO's simulation runs in which a pixel burns, per year (0.004 = 0.4 %
  a year, roughly once in 250 years).
- **Fire Weather Index (FWI):** a daily rating of how weather (heat, dryness, wind) favors fire spread, regardless
  of what fuel is there.
- **HUC-12:** the smallest standard US watershed unit (typically 40–160 km²).

Catalog IDs in brackets (F1, F4, ...) refer to the Arctic-EDS Candidate Data Catalog. It lists the wildfire hazards
as fire, smoke, visibility and travel-surface obstruction, affecting above-ground infrastructure, personnel,
equipment and land/air travel.

## 1. Decide first: what does "High wildfire hazard" mean here?
- **Likely to burn on the site itself** (pixel or small area), **fire nearby** (smoke, access, evacuation: a 10–25 km
  neighbourhood), or **fire becoming more common** (change)?
- Smoke and visibility are in the catalog's hazard list but not in ALFRESCO: in or out of this index?
- The answer picks the map scale and whether a change or a level variant leads.

## 2. Where we start
`flam-future` (2040–2069 level) and `flam-change` (since 1980–2008). Both use pixels on the map and the watershed
average at the point.

## 3. Variant backlog
Priority 1 = local or cached data, no new requests · 2 = needs server requests (ask first; sizes from the earlier
statewide flammability request, 19 MB each) or a metadata check · 3 = needs new data or more design.

| Proposed id | Idea | Data | Cost | Priority |
|---|---|---|---|---|
| `flam-area-10km` | flammability averaged over a 10 km radius (map and point agree; follows SNAP's advice) | cached 2040–2069 grid | local | 1 |
| `flam-area-25km` | same, 25 km ("fire nearby") | cached | local | 1 |
| `fire-interval` | years between fires (1 / flammability, capped at e.g. 1000 yr): easier to explain | cached | local | 1 |
| `flam-change-area-10km` | change, area-averaged (raw change is noisy: a third of pixels are 0 either way) | cached | local | 1 |
| `flam-models-agree` | how many of the 5 models put the cell in High (0–5) | ALFRESCO era 3, models 2–6, RCP 4.5 | 5 requests, ~95 MB | 2 |
| `flam-rcp85` | 2040–2069 under RCP 8.5 | ALFRESCO scenario 3 | 1 request | 2 |
| `flam-late-century` | 2070–2099 | ALFRESCO era 4 | 1 request | 2 |
| `fwi-change` | change in days with high fire weather (CMIP6; ~25 km, coarser than the others) | [F4] CMIP6 CFFDRS fire weather indices (Rasdaman `cmip6_fwi` and parts) | metadata check, then a few requests | 2 |
| `veg-shift` | share of forest projected to change type (fuel change) | [F3] Rasdaman `alfresco_vegetation_type_percentage` | metadata check, then requests | 3 |
| `recent-burn` | lower near-term hazard where fire burned recently | [F1] AICC fire perimeters 1940–2021 (SNAP-owned; the API is point-only, so statewide needs the file) | ask SNAP for the file | 3 |
| `smoke-days` | days with heavy smoke (historical only, ~60 km; not SNAP) | [F6] PM2.5 GEOS-Chem 2003–2020 | new download | 3 |

## 4. How we'll compare variants
- **Standard comparison** (was the app's **Compare variants** section; removed 2026-10-30, in git history): side-by-side maps, distributions, class shares statewide and by
  region (Arctic / Interior / West / South), class agreement between variants, values at the preset places.
- **Reality check:** does the 1980–2008 historical run put fire where fire actually burned? Compare with observed
  burned area by region: [F1] AICC perimeters (1980–2008 overlap) and [F7] Arctic Boreal Burned Area (2002–2022,
  ~500 m, not SNAP).
- **Explainability:** can each class at a place be said in one sentence?

## 5. Decisions for the team
1. Meaning of "High" (section 1).
2. Pixels vs area averages for the map (DATA_ISSUES #7).
3. Whether fire weather (CMIP6) can sit beside ALFRESCO (CMIP5-era models) in one index.

## 6. First session
1. Build `flam-area-10km`, `flam-area-25km`, `fire-interval`, `flam-change-area-10km` (local, about an hour).
2. Publish; compare with the current variants in the app at the preset places.
3. Ask: OK for the 5-model and RCP 8.5 requests (~115 MB, 6 requests)? Metadata check of `cmip6_fwi`? Can SNAP
   share the AICC perimeter file [F1]?
