# Toy Environmental Hazard Index

A "fingerpaint" prototype: three indices (Wildfire, Erosion, Permafrost), each turned into Low / Medium / High,
combined by a rule you choose on screen into one Environmental Hazard class. Not rigorous and not for decisions.
Data-structure caveats are listed in [DATA_ISSUES.md](DATA_ISSUES.md).

Each index, and the rule that combines them, is its own workstream with several **variants** (candidate versions)
to compare. The app shows every variant, so new ones appear as soon as they are built.

| Workstream | Question, variants, open questions | Decisions |
|---|---|---|
| Wildfire | [wildfire/README.md](wildfire/README.md) | [DECISIONS](wildfire/DECISIONS.md) |
| Erosion | [erosion/README.md](erosion/README.md) | [DECISIONS](erosion/DECISIONS.md) |
| Permafrost | [permafrost/README.md](permafrost/README.md) | [DECISIONS](permafrost/DECISIONS.md) |
| Combining | [composite/README.md](composite/README.md) | [DECISIONS](composite/DECISIONS.md) |

## Using the app
**Shared link** (claude.ai; shared with "anyone with the link"): https://claude.ai/artifact/BUwzxzSDTSzFa6exz8zwAN.
It holds every variant and loads each one when someone picks it. Watershed (HUC-12) wildfire values come from the SNAP
API only for the places in the list (fetched at build time); a clicked or typed point uses the map pixel, because
claude.ai pages can't reach other websites.

**Download** (offline, or for people without claude.ai): `app/build/toy_index_app.html`, one file with the data built
in; on GitHub use **Download raw file** and double-click it. It holds only the variants marked `in_single_file` (about
six fit) and asks the SNAP API for watershed values at any point.

- **Preset** (top right): a named set of variants, plus class boundaries and rule if the preset sets them. Open one
  directly with a link ending in `#preset-<id>`, e.g. `#preset-change`. Picking variants by hand shows "Custom mix".
- **Point** (top left): pick a place, type a latitude/longitude, or click any map. The badge shows the point's
  Environmental Hazard; the table shows each index's value and class.
- **Maps**: Alaska, a region around the point and a local area (sizes adjustable). The tabs switch between the hazard
  and the three indices. Hover for values.
- **Index cards** (bottom): the dropdown picks the variant; sliders or typed numbers move the Low/Medium and
  Medium/High boundaries (kept per variant). The histogram shows how Alaska's land is spread across values.
- **Combining rule** (bottom right): pick a rule and adjust its numbers. The grid shows all 27 combinations and the
  hazard each one gets; click a cell to set it by hand.
- **Copy settings** gives a plain-text record, ending with the setup as a preset file (see
  [composite/README.md](composite/README.md)). Settings are remembered in your browser; **Reset all** (two clicks)
  restores the defaults.

## Building
```
micromamba run -n arcticdem-pisr python -I toy_index/build_variants.py   # new/missing variants -> <data>/toy_index/variants/
micromamba run -n arcticdem-pisr python -I toy_index/app/build_app.py    # -> app/build/toy_index_app.html + app/build/hosted/
```
`build_variants.py wildfire` builds one index; `--force` rebuilds. Then publish `app/build/hosted/` to the shared link
(Claude does this with the Artifact tool) and commit `app/build/toy_index_app.html`.

Open a built page with `#selftest` at the end of the address to print checks (projection, values at every place for
every preset, every rule, variant switching, API access) at the top of the page.

## Layout
| Path | Holds |
|---|---|
| `common/grid.py` | The common grid (GIPL 1 km, EPSG:3338) and land mask |
| `common/sources.py` | Cached Rasdaman requests and their label codes (no new requests unless `fetch=True`) |
| `common/data.py` | Readers that put each source on the common grid |
| `common/variant.py` | The variant contract (`variant.json` fields), registry and file I/O |
| `<index>/variants/<id>/` | One variant: `variant.json` (description, display, default boundaries, status) + `build.py` |
| `composite/presets/*.json` | Presets |
| `build_variants.py` | Builds variant grids |
| `app/` | `app_template.html` (the page), `build_app.py` (packs variants and presets into it) |
| `DATA_ISSUES.md` | Running list of data-structure issues |

Data used: Rasdaman coverages (10 cached statewide requests), local GIPL GeoTIFFs, NOAA Atlas 14 Vol. 7
(hdsc.nws.noaa.gov/pub/hdsc/data/ak/ak100yr24ha_ams.zip, in `<data>/noaa_atlas14/`), SNAP DOT netCDFs (local archive).
