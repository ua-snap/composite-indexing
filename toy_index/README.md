# Toy Environmental Hazard Index

A "fingerpaint" prototype: three datasets, each turned into a Low / Medium / High index, combined by a rule you choose
on screen into one Environmental Hazard class. Not rigorous and not for decisions. Data-structure caveats are listed in
[DATA_ISSUES.md](DATA_ISSUES.md).

## Using the app
Shared copy (private claude.ai page, share it from its Share menu): https://claude.ai/artifact/BUwzxzSDTSzFa6exz8zwAN.
On that page the wildfire point value comes from the SNAP API only for the preset places (fetched when the page was
built); a clicked or typed point uses the map pixel instead, because hosted pages can't call outside websites.

Open `build/toy_index_app.html` in a browser (Chrome, Firefox, Edge or Safari). It is a single 5 MB file with the data
built in: download it and double-click it. You need internet only for the wildfire point value (SNAP API).
On GitHub, open the file and use **Download raw file** (GitHub shows HTML as source code, not as a page). It is the only
tracked file in `build/` (force-added; the folder is otherwise ignored), so commit it again after each rebuild.

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

## Rebuilding (Chinook)
```
micromamba run -n arcticdem-pisr python -I toy_index/fetch_statewide.py   # cached: no new requests once fetched
micromamba run -n arcticdem-pisr python -I toy_index/build_grids.py       # -> <data>/toy_index/grids_1km.npz
micromamba run -n arcticdem-pisr python -I toy_index/build_app.py         # -> toy_index/build/toy_index_app.html
```
`app_template.html` holds the page; `build_app.py` injects the data. Open the built page with `#selftest` at the end
of the address to print checks (projection, decoded values, every rule, API access) at the top of the page.

| File | Does |
|---|---|
| `fetch_pilot.py` | 100 km test window at Fairbanks (Rasdaman), plus the server label codes |
| `fetch_statewide.py` | Statewide flammability + 24 h / 100-yr precipitation (9 cached requests) |
| `build_grids.py` | Puts all three on the GIPL 1 km grid (fixes the transposed precipitation GeoTIFFs) |
| `build_app.py`, `app_template.html` | Build the single-file app |
| `DATA_ISSUES.md` | Running list of data-structure issues |
