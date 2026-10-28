# Environmental Hazard Index: team workbench

Three indices (Wildfire, Erosion, Permafrost), each turned into Low / Medium / High, combined by a rule into one
Environmental Hazard class. A working index the team uses to work out how the real one should be built. Data-structure
caveats are listed in [DATA_ISSUES.md](DATA_ISSUES.md).

Each index, and the rule that combines them, is its own workstream with several **variants** (candidate versions)
to compare. The app shows every variant, so new ones appear as soon as they are built.

| Workstream | Question, variants, open questions | Plan of work | Decisions |
|---|---|---|---|
| Wildfire | [wildfire/README.md](wildfire/README.md) | [PLAYBOOK](wildfire/PLAYBOOK.md) | [DECISIONS](wildfire/DECISIONS.md) |
| Erosion | [erosion/README.md](erosion/README.md) | [PLAYBOOK](erosion/PLAYBOOK.md) | [DECISIONS](erosion/DECISIONS.md) |
| Permafrost | [permafrost/README.md](permafrost/README.md) | [PLAYBOOK](permafrost/PLAYBOOK.md) | [DECISIONS](permafrost/DECISIONS.md) |
| Combining | [composite/README.md](composite/README.md) | [PLAYBOOK](composite/PLAYBOOK.md) | [DECISIONS](composite/DECISIONS.md) |

Each playbook: what "High" should mean (decide first), a ranked variant backlog with data source and cost (catalog
IDs refer to the Arctic-EDS Candidate Data Catalog, copy saved 2026-10-27 as
[arctic_eds_candidate_data_catalog.csv](arctic_eds_candidate_data_catalog.csv)), how variants get compared, decisions for the team, and the first
session's work. The loop for every workstream: build variants → publish to the shared link → the team compares them in the
app, picks one, sets its boundaries and saves the decision → Claude copies the decisions back into the repo.

## Using the app (team workbench)
**Shared link** (claude.ai): https://claude.ai/artifact/BUwzxzSDTSzFa6exz8zwAN. Tabs along the top:

- **Summary**: the team's saved decisions for a non-technical reader. The hazard map, the share of Alaska's land in
  each class (statewide, by region, at named places), and the three indices → rule as a flow, each with what High
  means and the team's reason. Anything not yet decided shows the repo's starting point and says so.
- **Wildfire / Erosion / Permafrost**: one page per index. One card per variant (**Variant A, B, …**): class map,
  description, histogram, and sliders or typed numbers for the Low/Medium and Medium/High boundaries. Tick **Use this
  variant** on the one the index should use. Below, **Compare variants** updates as the boundaries move: class shares
  by region, agreement between every pair (same class, Low vs High, rank correlation), a map of where two variants
  differ, and values at named places.
- **Environmental Hazard**: the three chosen variants and their boundaries, read only (change them on the index
  pages). Pick the combining rule and adjust it; the grid shows all 27 combinations (click a cell to set it by hand).
  Hazard shares by region, what makes cells High, and maps at three scales with a point inspector.

**Team decisions.** Moving sliders, ticking a variant or changing the rule is a personal draft (kept in your browser,
marked "Your unsaved changes" and with a dot on the tab). **Save as team decision** (with a short "why") makes it the
team's: everyone with the link then sees it on every tab, the Summary included. **Discard my changes** returns to the
team decision. Saving needs Contributor access or higher; viewers see the decisions read only. Every save is also
kept in a history the team (and Claude) can read.

**Download PDF** (Summary page, top right): the saved team decisions as a PDF, to keep after each work session.
Page 1 is the summary, page 2 how the index is built (with each reasoning note and all 27 rule combinations), then a
specification with each chosen variant's method, sources and exact boundaries, the full rule, and the decisions as
JSON in the same shape as `composite/decisions.json`: enough to rebuild the index from scratch.

**Start over** (bottom of the Summary page, Editors and the owner only): **Reset all team decisions** (two clicks)
clears every saved decision and reasoning note; the history is kept. Claude can also do this with the ArtifactData
tool (and keep a backup copy in the data directory first).

Watershed (HUC-12) wildfire values come from the SNAP API only for the named places (fetched at build time); other
points use the 1 km cell, because claude.ai pages can't reach other websites.

## Building
```
micromamba run -n arcticdem-pisr python -I toy_index/build_variants.py   # new/missing variants -> <data>/toy_index/variants/
micromamba run -n arcticdem-pisr python -I toy_index/app/build_app.py    # -> app/build/hosted/
```
A new variant needs a unique `letter` in its variant.json (never reuse a retired variant's letter). Claude publishes
`app/build/hosted/` (index.html + data/*.png) to the shared link with the Artifact tool, keeping the team record.
After the team saves decisions, Claude reads them from the app and writes them to
[composite/decisions.json](composite/decisions.json), the app's starting point for anything the team hasn't decided.

Open `app/build/hosted/_local.html#selftest` from a local web server to print checks (class shares and agreement with
default boundaries, values at places, projection).

## Layout
| Path | Holds |
|---|---|
| `common/grid.py` | The common grid (GIPL 1 km, EPSG:3338) and land mask |
| `common/sources.py` | Cached Rasdaman requests and their label codes (no new requests unless `fetch=True`) |
| `common/data.py` | Readers that put each source on the common grid |
| `common/variant.py` | The variant contract (`variant.json` fields), registry and file I/O |
| `common/places.py` | The app's named places, snapped to the nearest cell with data |
| `<index>/variants/<id>/` | One variant: `variant.json` (description, display, default boundaries, status) + `build.py` |
| `<index>/index.json` | The index's name and question (`composite/` = the hazard) |
| `composite/decisions.json` | The team's decisions as copied from the app (the app's starting point) |
| `build_variants.py` | Builds variant grids |
| `app/` | `app_template.html` (the page), `build_app.py` (packs variants, questions and decisions into it) |
| `DATA_ISSUES.md` | Running list of data-structure issues |

Data used: Rasdaman coverages (10 cached statewide requests), local GIPL GeoTIFFs, NOAA Atlas 14 Vol. 7
(hdsc.nws.noaa.gov/pub/hdsc/data/ak/ak100yr24ha_ams.zip, in `<data>/noaa_atlas14/`), SNAP DOT netCDFs (local archive).
