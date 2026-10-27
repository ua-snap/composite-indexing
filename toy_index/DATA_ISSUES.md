# Toy index: data structure issues (running list)

**Short answer:** the three datasets behind the toy index (wildfire, erosion, permafrost) were built by different
projects for different purposes. They don't share one model set, emissions scenario, time window, grid, unit or kind
of number. Even a "fingerpaint" index has to paper over these gaps, so this list records each gap and how the toy
handles it. Anything we'd need to fix properly in a real index is marked **real fix needed**.

Started 2026-10-27; add to it as we go.

## The three datasets

| Index | Dataset (SNAP) | What one value means | Native grid | Time window | Climate models | Scenario |
|---|---|---|---|---|---|---|
| Wildfire | ALFRESCO relative flammability | Average chance a pixel burns in a year (0.004 = 0.4 %/yr) | 1 km | 2040–2069 (fixed) | 5-model average | RCP 4.5 |
| Erosion | DOT precipitation frequency ("DOT-Precip") | Rain depth of the 24-hour storm expected once per 100 years (inches) | ~480 m | 2050–2079 (fixed) | GFDL-CM3 + NCAR-CCSM4 only (we average them) | **RCP 8.5 only** |
| Permafrost | GIPL 2.0 ground temperature at 1 m | Mean annual ground temperature (°C) | 1 km | annual; we average 2040–2069 | 5-model average | RCP 4.5 |

**Key terms**
- **RCP 4.5 / 8.5:** emissions scenarios: "middle of the road" and "high".
- **Ensemble average:** the average of several climate models. It can be made *before* running a model (average the
  climate, then run once) or *after* (run each model, then average the results). The two are not the same.
- **Return interval:** "100-year storm" = a storm with a 1 % chance of happening in any given year.
- **HUC-12:** the smallest standard US watershed unit (typically 40–160 km²).

## Issues so far

| # | Issue | Where it shows up | What the toy does | |
|---|---|---|---|---|
| 1 | **Model mismatch** | Erosion has only 2 models; the others use a 5-model average. Wildfire and GIPL "5-model averages" may be built differently (averaged inputs vs averaged outputs; not yet confirmed). | Average the 2 erosion models; label it. | real fix needed |
| 2 | **Scenario mismatch** | Erosion exists only for RCP 8.5 (WRF downscaling); the others use RCP 4.5. | Use RCP 8.5 for erosion; label it. | real fix needed |
| 3 | **Era mismatch** | Wildfire is fixed at 2040–2069 and erosion at 2050–2079; GIPL is annual. | Use the nearest era for each; GIPL averaged to 2040–2069 to match wildfire. | real fix needed |
| 4 | **Grid mismatch** | Three grids: wildfire 1 km, GIPL 1 km (offset ~430 m from wildfire), erosion ~480 m. All EPSG:3338 but cell edges don't line up. | Everything moved onto the GIPL 1 km grid (wildfire: nearest cell; erosion: averaged). | ok for toy |
| 5 | **Extent mismatch** | Wildfire stops ~10 km short of the GIPL box's south edge and includes Yukon; erosion covers ocean and Canada; GIPL is Alaska land only. | Cut everything to the GIPL land mask. | ok for toy |
| 6 | **Different kinds of number** | A yearly probability (wildfire), a rare extreme event (erosion) and an average condition (permafrost). "High" means something different in each. | Each index gets its own Low/Med/High breaks. | discuss |
| 7 | **Pixel vs area values** | SNAP says single ALFRESCO pixels aren't statistically meaningful; their API only gives HUC-12 averages. | Maps show raw pixels; the point rating uses the API's HUC-12 average. So the point rating can differ from the pixel under it, and HUC averages are smoother (fewer "High" points). | discuss |
| 8 | **Holes in the data** | Wildfire: ~20 % of land has no value (not burnable: water, ice, rock, towns). GIPL: "stuck" model cells and a 2 km border around them are masked (D17); ~6 % of land, including downtown Fairbanks. | Holes shown in grey. Default point moved to Fort Wainwright (clean GIPL cell). | discuss |
| 9 | **"No value" vs "zero"** | Wildfire has both blank cells (not burnable) and true zeros (burnable, but never burned in the simulations); 26 % of land is exactly 0. Because of that pile of zeros, a "thirds of the land" default puts the Low/Medium boundary at 0.0001, so Low means "essentially never burns". | Zeros are Low; blanks are grey. Team to set the boundary. | discuss |
| 10 | **What "high" means for permafrost** | Ground above 0 °C at 1 m usually means no permafrost there, so nothing is left to thaw. That's 58 % of mapped land by 2040–2069. A warm cell may be "already thawed / not applicable" rather than "high hazard". | Treated as High for now. | discuss |
| 11 | **Units** | Flammability is a fraction; erosion is stored in thousandths of an inch on Rasdaman but returned in **mm** by the API; GIPL is °C. | Converted to inches; API-vs-server unit difference noted in code. | ok for toy |
| 12 | **Uncertainty only for erosion** | Erosion has 90 % confidence bounds (`pf_lower`, `pf_upper`); the others don't. | Ignored. | later |
| 13 | **Hidden choices inside datasets** | Wildfire: SNAP files come in 3 fire-management versions, but Rasdaman serves one (which one isn't stated). Erosion: we picked one storm length (24 h) and one return interval (100 yr) out of 15 × 9. | Use what Rasdaman serves; 24 h / 100 yr fixed. | real fix needed |
| 14 | **Labels and encodings** | GIPL year labels are 20 years late (GIPL_ISSUE_3). Rasdaman axes are coded by number, sometimes in odd orders (erosion: 24 h = index 3, 60 min = 12). | Labels decoded from server metadata; all checked against the API at Fairbanks. | ok for toy |
| 15 | **Server output quirk** | Rasdaman returns erosion GeoTIFFs **transposed** (rows and columns swapped). A square test window hides it. | Transposed when read; checked against the land mask and the API. | ok for toy |

## Caveats
- The list covers structure (how the datasets fit together), not whether each dataset is right.
- The point checks were done at Fairbanks only.

## Methods footnote
Sources: Rasdaman (Zeus) coverages `alfresco_relative_flammability_30yr` (era 3, model 1, scenario 1) and
`dot_precip` (field `pf`, era 1, duration 3 = 24 h, interval 100, models 0 and 1), fetched once statewide in 9
requests (`fetch_statewide.py`); GIPL `magt1m` local GeoTIFFs read with `gipl_file_year`. Common grid built by
`build_grids.py` → `<data>/toy_index/grids_1km.npz`. Server label codes come from each coverage's DescribeCoverage
`ras:Encoding` (saved in `<data>/rasdaman_meta/`). Checks against earthmaps.io at Fairbanks: erosion 12/12 values
equal; wildfire 10 km mean 0.0043 vs HUC-12 API 0.0042.
