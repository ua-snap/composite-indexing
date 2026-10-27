# Toy Environmental Hazard Index

A "fingerpaint" prototype: three datasets, each turned into a Low / Medium / High index, combined by a rule you choose
on screen into one Environmental Hazard class. Not rigorous and not for decisions. Data-structure caveats are listed in
[DATA_ISSUES.md](DATA_ISSUES.md).

## Using the app
Shared copy (private claude.ai page, share it from its Share menu): https://claude.ai/artifact/BUwzxzSDTSzFa6exz8zwAN.
On that page the wildfire point value comes from the SNAP API only for the preset places (fetched when the page was
built); a clicked or typed point uses the map pixel instead, because hosted pages can't call outside websites.

Open `build/toy_index_app.html` in a browser (Chrome, Firefox, Edge or Safari). It is a single 12 MB file with the data
built in: download it and double-click it. You need internet only for the wildfire point value (SNAP API).
On GitHub, open the file and use **Download raw file** (GitHub shows HTML as source code, not as a page). It is the only
tracked file in `build/` (force-added; the folder is otherwise ignored), so commit it again after each rebuild.

- **Classes built on** (top right): **Future values** (mid-century amounts) or **Change over time** (how much each
  index changes from a baseline; see below). Each mode keeps its own class boundaries. Add `#mode=delta` to the address
  to open in change mode.
- **Point** (top left): pick a place, type a latitude/longitude, or click any map. The badge shows the point's
  Environmental Hazard; the table below shows each index's value and class.
- **Maps**: Alaska, a region around the point and a local area (sizes adjustable). The tabs switch between the hazard
  and the three indexes. Hover for values.
- **Index cards** (bottom): drag the sliders or type numbers to move the Low/Medium and Medium/High boundaries. The
  histogram shows how Alaska's land area is spread across values; the bar shows the share in each class.
- **Combining rule** (bottom right): pick a rule and adjust its numbers. The grid shows all 27 combinations
  (Wildfire × Erosion × Permafrost) and the hazard each one gets; click a cell to set it by hand.
- **Copy settings** gives a plain-text record of the current boundaries and rule (paste it into notes). Settings are
  remembered in your browser; **Reset all** restores the defaults.

Point values: erosion and permafrost come from the 1 km map cell. Wildfire comes from the SNAP API's watershed
(HUC-12) average, because SNAP advises against reading single ALFRESCO pixels; the map itself shows raw pixels.

### Change over time
| Index | From → to | Measured as |
|---|---|---|
| Wildfire | 1980–2008 historical run → 2040–2069 | change in chance of burning per year (absolute; a third of land is unchanged) |
| Erosion | NOAA Atlas 14 → 2050–2079 | % change in the 24-hour, 100-year storm. SNAP's DOT amounts are Atlas 14 × the climate model's change since 1979–2005 (Bieniek et al. 2022), so this is the model's projected change |
| Permafrost | 2004–2015 → 2040–2069 | "progress to thaw": warming at 1 m as a % of the distance to 0 °C. 100 % = crosses 0 °C. Ground not frozen at the start is Low (no permafrost to lose) |

Defaults: permafrost Low ≤ 50 % < Medium ≤ 100 % < High; wildfire Low = no increase, increases split at their
median; erosion statewide thirds.

## Rebuilding (Chinook)
```
micromamba run -n arcticdem-pisr python -I toy_index/fetch_statewide.py   # cached: no new requests once fetched
micromamba run -n arcticdem-pisr python -I toy_index/build_grids.py       # -> <data>/toy_index/grids_1km.npz
micromamba run -n arcticdem-pisr python -I toy_index/build_delta.py       # -> <data>/toy_index/grids_delta_1km.npz
micromamba run -n arcticdem-pisr python -I toy_index/build_app.py         # -> toy_index/build/toy_index_app.html
```
`app_template.html` holds the page; `build_app.py` injects the data. Open the built page with `#selftest` at the end
of the address to print checks (projection, decoded values, every rule, API access) at the top of the page.

| File | Does |
|---|---|
| `fetch_pilot.py` | 100 km test window at Fairbanks (Rasdaman), plus the server label codes |
| `fetch_statewide.py` | Statewide flammability (2040–2069 and the 1980–2008 baseline) + 24 h / 100-yr precipitation (10 cached requests) |
| `build_grids.py` | Puts all three on the GIPL 1 km grid (fixes the transposed precipitation GeoTIFFs) |
| `build_delta.py` | Change-over-time grids: wildfire baseline (1 cached Rasdaman request), NOAA Atlas 14 (download: hdsc.nws.noaa.gov/pub/hdsc/data/ak/ak100yr24ha_ams.zip), GIPL 2004–2015 |
| `build_app.py`, `app_template.html` | Build the single-file app |
| `DATA_ISSUES.md` | Running list of data-structure issues |
