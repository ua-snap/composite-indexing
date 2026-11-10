# Wildfire index

**Question:** which number best says "this place's wildfire hazard is low / medium / high (or rising)"?

## Variants
| id | What it is | Status |
|---|---|---|
| Letter | id | What it is |
|---|---|---|
| A | `flam-future` | ALFRESCO relative flammability, 2040–2069 (5-model average, RCP 4.5); point value = SNAP API watershed (HUC-12) average, map = 1 km pixels |
| B | `fwi-future` | Fire Weather Index (FWI), mean of every April–October day 2040–2069, 4 CMIP6 models, SSP5-8.5 (~25 km, interpolated to 1 km) |
| C | `fwi-peak-week` | FWI in the worst week of a typical season: highest 7-day centred rolling mean of the 2040–2069 mean daily curve (per model, then the 4-model mean) |
| D | `fwi-high-days` | Days per summer (June–August) with FWI ≥ 18 (High, Very High or Extreme fire danger, Alaska Fire Danger Operating Plan) |

B–D: land outside the release's boreal domain (61 % of Alaska) has no fire weather data and is a fixed **Low**
("outside the boreal area"; user 2026-11-10). C and D follow the SNAP API's operations (earthmaps.io/fire_weather:
`7_day_rolling_average`, `summer_fire_danger_rating_days`; code in github.com/ua-snap/data-api `routes/fire_weather.py`,
FWI ratings in `luts.py`: Low < 9, Mod 9–18, High 18–28, VHigh 28–35, Ext ≥ 35), computed from the local file
(the API reads the same data from Rasdaman), so no server requests.

Retired 2026-11-10: `flam-change` (change since the 1980–2008 historical run). A place that burns often both then and
at mid-century shows no change and would be rated Low, though it is still highly flammable.

**Fire weather data (B):** SNAP's CMIP6 fire weather release (Young, Littell & Rupp 2025, doi:10.5066/P1AAMRUF), read
from the local copy `/import/beegfs/CMIP6/arctic-cmip6/cmip6_fwi/data_release_v2/cmip6_fwi/combined/cmip6_fwi_combined.nc`
(the same data as Rasdaman `cmip6_fwi`: no server requests). Daily, April–October only, 1980–2099, 0.25°, models
CNRM-CM6-1-HR, EC-Earth3-Veg, MPI-ESM1-2-HR, MRI-ESM2-0 (SSP5-8.5) + ERA5 (historical). Summarized by
`scripts/01_data/summarize_fwi.py` (`slurm/21_summarize_fwi.slurm`) into `<data>/fwi/fwi_alaska_2040-2069_ssp585.nc`:
per-model monthly means, the mean of each season day (for rolling averages) and June–August days per fire danger
rating, so other summaries need no re-read.

**Findings (2026-11-10):**
- **Boreal region only:** FWI has a value on 39 % of Alaska's land (Arctic 7 %, Interior 73 %, West 40 %, South
  14 %). The yearly files, the older release and the weather inputs all share this mask: no other local or Rasdaman
  source covers tundra or the coast.
- Values are low as a season mean (median 3.9; 90 % of covered land 2.3–6.7); highest in the eastern Interior
  (Yukon Flats, up to ~11). At Fairbanks the season peaks in May–June.
- The four models agree on the pattern (rank correlation 0.90–0.99 between 0.25° cells); MRI-ESM2-0 runs lowest
  (median 2.6 vs 4.1–4.7).
- A vs B where both have values: rank correlation 0.33; same class (each at its own thirds) on 39 % of that land.
- **B, C and D are nearly the same map** (rank correlation 0.96–0.98; same third on 84–91 % of boreal land); each
  is equally far from A (0.33–0.35). The statistic changes the numbers, not the pattern. With the outside as Low,
  each puts 74 % of Alaska in Low (Arctic 96–99 %, South 95–96 %, Interior ~45 %).
- C: median 8.6 (thirds 7.5 / 10.1); Fairbanks 17.8, peak in late May (MRI-ESM2-0 mid-May). D: median 6.1 days
  (thirds 4.1 / 8.6); Fairbanks 20.7 days. MRI-ESM2-0 is much milder (median 0.7 high-danger days vs 7.6–9.8);
  model rank correlation 0.77–0.94 (C), 0.78–0.97 (D).

## Open questions
- Pixels vs watershed averages: SNAP says single ALFRESCO pixels aren't meaningful ([DATA_ISSUES](../DATA_ISSUES.md) #7).
  Variant idea: smooth the map to watershed or 10 km averages.
- "No value" vs zero: 26 % of land is exactly 0 (#9).
- Which fire-management version Rasdaman serves (#13).
- FWI outside the boreal region is Low (#20): acceptable for the Arctic and Y-K Delta tundra, which do burn?
- B, C or D: the maps agree, so choose by which number is easiest to explain (D: "days of high fire danger").
- FWI is SSP5-8.5 only (4 CMIP6 models); Variant A and the permafrost index are RCP 4.5 (5 CMIP5 models) (#1, #2).

## Adding a variant
Copy a folder in `variants/`, edit `variant.json` (fields in `../common/variant.py`) and `build.py`, then run
`python -I toy_index/build_variants.py wildfire` and `python -I toy_index/app/build_app.py`.
