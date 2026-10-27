# Permafrost playbook

**Short answer:** this workstream has the most to build on. The Permafrost Thaw Index (PTI, `docs/PTI.md`) already
answers "how susceptible to thaw is the permafrost here, if it is there?" with a two-way table (how warm the ground
is today × how much it warms), and its classes are on the same 1 km grid. Next we bring PTI in as variants, add
simple GIPL measures that the team can read directly (when does the ground thaw, how deep does it thaw), and check
how much the answer depends on the model. Everything in the first session is local.

**Key terms**
- **GIPL:** the permafrost model behind SNAP's ground-temperature maps (1 km, 2021–2120 files = climate 2001–2100).
- **MAGT:** mean annual ground temperature at a depth (1 m in the toy). Above 0 °C means no permafrost at that depth.
- **Active layer / permafrost top:** the ground that thaws each summer; the depth where permafrost starts.
- **Talik:** unfrozen ground within permafrost; forms as permafrost degrades.

Catalog IDs in brackets (P1, P7, ...) refer to the Arctic-EDS Candidate Data Catalog. It lists the permafrost hazards
as thermokarst, thaw, erosion, travel-surface degradation and presence/absence, affecting infrastructure and land
travel. Today's GIPL data is [P1]; the ESA CCI data we already hold is [P2].

**Name clash:** the catalog's [P3] "Permafrost Thaw Index" (Guo et al. 2026, Zenodo, built from ESA CCI 1997–2023) is
a different product from our PTI (`docs/PTI.md`). We should rename ours or always cite which one.

## 1. Decide first: what does "High permafrost hazard" mean here?
- **Ground likely to thaw** (susceptibility: PTI's question), **ground already thawing** (change in thaw depth,
  talik), or **damage potential** (thaw × ice-rich ground × what's built there)?
- Ground not frozen at the start: Low (current choice) or its own "no permafrost" class?

## 2. Where we start
`temp-1m-future` (1 m temperature, 2040–2069) and `thaw-progress` (warming as a share of the distance to 0 °C). Both
mask GIPL's stuck cells (D17).

## 3. Variant backlog
Priority 1 = local data or existing results · 2 = more work · 3 = new data.

| Proposed id | Idea | Data | Cost | Priority |
|---|---|---|---|---|
| `pti-v2` | PTI classes, GIPL warming (V2) | `<data>/results/t4/index_variants.nc` (eras 2026–2050, 2051–2080) | local | 1 |
| `pti-v1` | PTI classes, air-temperature warming (V1) | same | local | 1 |
| `thaw-year` | first climate year when 1 m stays above 0 °C (5 years running) | local GIPL `magt1m` | local | 1 |
| `permafrost-top-change` | deepening of the permafrost top (active layer), m | local GIPL `permafrosttop` | local | 1 |
| `talik-2040-2069` | talik thickness at mid-century | local GIPL `talikthickness` | local | 1 |
| `temp-surface-future` | ground surface temperature (what PTI uses, D18) | local GIPL `magtsurface` | local | 1 |
| `thaw-progress-models` | thaw progress for GFDL-CM3 and NCAR-CCSM4 separately | local GIPL runs | local | 2 |
| `esa-start` | observed starting temperature (ESA CCI 2000–2023) + GIPL change | [P2] local ESA + GIPL (`docs/ESA_GIPL_SPLICING.md`) | local, more work | 2 |
| `esa-trend` | observed warming trend 1997–2023 at 1 m (what's already happening) | [P2] local ESA (2000–2023 held) | local | 2 |
| `terrain-adjusted` | thaw progress nudged by sun exposure (south slopes thaw first) | local `tii_1km` | local, design needed | 2 |
| `alt-change-li` | active layer thickness change to 2100 (CMIP6, 1 km) | [P7] Li et al. 2022 (not SNAP) | new download | 2 |
| `guo-thaw-index` | the published observed thaw index | [P3] Guo et al. 2026 (Zenodo) | new download | 2 |
| `thermokarst-landscape` | where the terrain is prone to thermokarst (a ground-ice proxy) | [P9] Olefeldt et al. 2016 (vector) | new download; rasterize | 3 |
| `ground-ice` | weight by ground-ice content | permafrost ground-ice map (NSIDC) | new download | 3 |

## 4. How we'll compare variants
- **Standard comparison** (`compare.py`): maps, distributions, class shares by region, class agreement, preset places.
- **Reality check:** GIPL against measured borehole temperatures (`<data>/boreholes/`, TSP network), ESA CCI [P2]
  and the Obu et al. 2019 permafrost zones [P8]. Coarse model products [P5, P6] (~50 km) can show whether GIPL's
  statewide trend is typical.
- **Consistency with PTI decisions:** PTI already weighed V1 vs V2 (Q19, open) and the stuck cells (D17); variants
  here should not reopen those without reason.

## 5. Decisions for the team
1. Meaning of "High" (section 1), and how "no permafrost at the start" is classed.
2. Use PTI as the permafrost index outright (it's the most developed), or keep a simpler GIPL measure?
3. PTI eras (2026–2050, 2051–2080) vs the toy's 2040–2069: re-run PTI for 2040–2069, or accept the nearest era?
4. Our PTI's name, given Guo et al.'s published Permafrost Thaw Index [P3].

## 6. First session
1. Build `pti-v2`, `pti-v1` (map the netCDF variable names to V1/V2 first), `thaw-year`, `permafrost-top-change`,
   `talik-2040-2069`, `temp-surface-future`.
2. Publish; compare PTI classes with `thaw-progress` at the preset places.
3. Note where the simple measures and PTI disagree; that's the team discussion.
