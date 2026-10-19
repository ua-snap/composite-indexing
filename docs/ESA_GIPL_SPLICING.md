# Joining today's ground temperature (ESA CCI) to projections (GIPL): the delta change method

**Question:** the index needs one continuous record of ground surface temperature, from today (ESA CCI Permafrost,
observation-based, 2000–2023) into the future (GIPL 2.0 projections, 2021–2120). The two datasets come from different
models and inputs. How should they be joined?

**Answer:** use the **delta change method** (SNAP's "delta method"), plus a "bridge" derived from the climate change signal. This keeps ESA's level for today and adds only the
*change* projected by the models.

---

## Key terms, in plain language

- **Level:** the temperature itself (e.g. −2.5 °C).
- **Change (delta):** how much the temperature rises between a reference period and a future period (e.g. +3.0 °C).
- **Offset:** the difference between two datasets for the same place (GIPL − ESA).
- **Expected warming:** the air warming that the climate models project between two periods. When the two datasets
  describe different years, part of their difference is simply climate change, not disagreement.
- **Excess offset:** the offset minus the expected warming, i.e. the real disagreement between the datasets
  (section 2). It is a diagnostic only: the recommended method does not use it.
- **Bridge:** the expected warming from ESA's last decade (2014–2023) to GIPL's reference decade (2026–2035), about
  +1 °C. It is the same number as the expected warming in section 2, used to carry ESA's level forward to GIPL's
  reference decade, and it applies to every future year.
- **Start-up period:** a model's first years after it starts, while it is still settling in; they do not behave like
  the rest of the run and are not used.
- **Spearman ρ:** whether two maps rank places in the same order, from −1 to +1 (see [CORRELATION.md](CORRELATION.md)).
- **Delta change method:** future = today's observed level + the change the model projects. The model contributes
  only its change, not its level.

## Data

| | ESA CCI Permafrost v5 | GIPL 2.0 (SNAP) |
|---|---|---|
| What | ground surface temperature (GST), 1 km | ground surface temperature (MAGT surface), 1 km |
| Years | 2000–2023 (here: 2014–2023 mean) | 2021–2120 (here: 2026–2035 reference) |
| Basis | satellite land surface temperature + permafrost model | climate projections (5-model average, RCP 4.5 / 8.5) + permafrost model |

Cells: everywhere ESA shows permafrost and GIPL behaves normally (≈ 724,000 cells; stuck cells excluded, see
[GIPL_ISSUE.md](GIPL_ISSUE.md)).

---

## 1. GIPL's first five years (2021–2025) are not usable

![ESA CCI and GIPL at three test areas](figures/t3_continuity.png)

Medians of 100 cells in each of three 10 × 10 km test areas (Brooks Range, Fairbanks, Denali).
- **At 1 m**, GIPL starts far from its later values and climbs for about five years (Denali, RCP 4.5: −4.4 °C in
  2021, −1.1 °C in 2025).
- **At the surface**, the first five years are out of line too: values rise until 2024–2025, then drop back by
  0.6–1.9 °C in 2026 (Denali: −0.2 °C in 2025, −1.9 °C in 2026). From 2026 on, both depths follow a steady trend.
- GIPL's set-up is not documented, so the cause is unknown. We treat **2021–2025 as a start-up period** and use
  **2026–2035** as GIPL's reference period.
- **This rules out a direct comparison with ESA:** the only years the two datasets share (2021–2023) fall inside
  GIPL's start-up period. Section 2 compares them fairly instead: GIPL 2026–2035 against ESA 2014–2023, after allowing
  for the warming expected between those periods.

## 2. GIPL and ESA levels do not match

### Comparing two different decades

The two records share no usable years (section 1): ESA ends in 2023 and GIPL is usable from 2026. So we compare
ESA's last decade (**2014–2023**) with GIPL's first usable decade (**2026–2035**). Their midpoints are 12 years apart.

The climate warms over those 12 years. **Even if the two datasets agreed perfectly, GIPL's decade should be warmer than
ESA's**, by about as much as the climate warmed in between. A straight comparison would mix two things: real
disagreement between the datasets, and climate change between the two decades. To separate them, we estimate the
warming between the decades and subtract it:

> **disagreement ("excess offset") = (GIPL 2026–2035 − ESA 2014–2023) − expected warming**

- **Expected warming:** for each cell, the air warming from 2014–2023 to 2026–2035 in SNAP's downscaled climate
  projections (5-model average, same scenario). About **+1.0 °C** statewide; 80 % of cells fall between +0.9 and
  +1.2 °C.
- **Worked example (statewide median, RCP 8.5):** GIPL is 0.2 °C *colder* than ESA. It should be about 1.0 °C
  *warmer*, so the disagreement is about **1.2 °C**.

Why this is a fair adjustment:
- **It only removes what climate change would produce.** It does not tune GIPL to match ESA.
- **It is small and nearly the same everywhere**, so it moves all cells by about the same amount. It cannot create
  the large cell-to-cell differences below, and it does not affect ρ, which compares the two maps as delivered.
- **It assumes the ground surface warms about as much as the air** over these 12 years. That is not exact (snow and
  vegetation sit in between), but over later decades GIPL's own surface warming stays within a few tenths of a degree
  of air warming on average ([PTI.md](PTI.md), section 2). An error of ±0.3 °C would still leave GIPL 0.9–1.5 °C
  colder than expected.
- **Skipping the adjustment would hide most of the problem:** the raw gap (0.2 °C) looks small only because a decade
  of warming happens to cancel most of GIPL's cold bias.

### Result

![ESA vs GIPL, same cells](figures/t3_splice_scatter.png)

![Excess offset map and by region](figures/t3_splice_map.png)

| Region | Cells | ESA vs GIPL, ρ | GIPL − ESA, as delivered | Expected warming | Excess offset, median | 10th – 90th percentile |
|---|---|---|---|---|---|---|
| Statewide | 724,326 | 0.85 | −0.2 °C | +1.0 °C | **−1.2 °C** | −2.8 to +0.5 °C |
| Arctic | 317,000 | 0.82 | 0.0 °C | +1.1 °C | −1.2 °C | −3.0 to +0.6 °C |
| Interior | 279,692 | **0.43** | −0.3 °C | +0.9 °C | −1.2 °C | −2.7 to +0.7 °C |
| West | 101,947 | 0.75 | −0.4 °C | +1.0 °C | −1.4 °C | −2.4 to −0.2 °C |
| South | 25,654 | **0.34** | +0.5 °C | +0.9 °C | −0.4 °C | −1.8 to +1.7 °C |

RCP 8.5 shown; RCP 4.5 is within 0.1 °C.
- GIPL is about **1.2 °C colder** than ESA would lead us to expect.
- The difference **varies a lot from cell to cell** (a 3 °C range between the 10th and 90th percentiles).
- In the **Interior and South**, the two datasets even disagree on *which places* are warmer (ρ 0.43 and 0.34).

## 3. Join methods compared

To build one record from today into the future, GIPL's values have to be put on ESA's footing. We tried four ways:

| Method | What it does to each cell's GIPL values (RCP 8.5) |
|---|---|
| No correction | Uses GIPL's temperatures as delivered. |
| Statewide offset | Adds the same number to every cell: GIPL's statewide median disagreement, **+1.2 °C**. |
| Regional offsets | Adds one number per region, that region's median disagreement: **Arctic +1.2, Interior +1.2, West +1.35, South +0.35 °C**. |
| Delta change method | Never uses GIPL's level. For each cell: (1) start from ESA's 2014–2023 level; (2) add the bridge (the expected warming from 2014–2023 to 2026–2035, ≈ +1 °C), giving the cell's estimated 2026–2035 level; (3) for any later year, add how much GIPL warms after 2026–2035. Steps 1–2 are the same for every year; only step 3 changes. |

**The delta change method, step by step.** An example cell with round numbers: ESA −2.0 °C (2014–2023), bridge
+1.0 °C, and GIPL −4.0 °C in 2026–2035 and −1.5 °C in 2051–2080 (a change of +2.5 °C). Joined 2051–2080 value:
−2.0 + 1.0 + 2.5 = **+1.5 °C**. GIPL's own −1.5 °C is never used, so its cold bias drops out; only the size of its
warming carries over.

![The delta change method for one example cell](figures/t3_delta_method_schematic.png)

*Panel 1: from GIPL we take only how much it warms after 2026–2035 (+2.5 and +3.5 °C here); its own temperatures,
including −4.0 °C for 2026–2035, are not used. Panel 2: the joined record starts from ESA (−2.0 °C), adds the bridge
to reach an estimated 2026–2035 level (−1.0 °C, the starting point for every later year), then adds GIPL's warming
from panel 1. The bridge is applied to ESA, never to GIPL.*

**The test:** if a join works, each cell's joined value for 2026–2035 should equal its ESA value plus the expected
warming. Any difference is an artificial step in the record at the join (a "jump") that is not climate. With an
offset, the jump is each cell's own disagreement minus the number added: the typical cell is fixed, but cells far from
the typical disagreement are not.

| Method | Jump, typical cell (median) | Jump, worst 10 % of cells (90th percentile) |
|---|---|---|
| No correction | 1.3 °C | 2.8 °C |
| Statewide offset | 0.8 °C | 2.2 °C |
| Regional offsets | 0.8 °C | 2.2 °C |
| **Delta change method** | **0 °C** | **0 °C** |

Statewide, RCP 8.5 (RCP 4.5 within 0.05 °C).
- **One number per region barely helps**, because the regions' typical disagreements are nearly the same (about
  −1.2 °C; only the South differs). The problem is the spread *within* each region, which no single number can fix.
- **Why the jump matters:** a jump goes straight into a cell's projected warming. The index's warming bands are 1 °C
  wide ([PTI.md](PTI.md)), so a 2 °C artificial jump in one cell in ten would move those cells by up to two classes.
- **The delta change method has no jump by construction**, because it never uses GIPL's level. That is not a free
  pass: it assumes GIPL's *changes* are right even where its *levels* are off, which cannot be tested (see Caveats).

![Test areas: ESA, raw GIPL and the delta change method](figures/t3_splice_pilots.png)

Raw GIPL (blue) runs below ESA (grey) in the Brooks Range and Denali test areas. The delta change method (orange,
from 2026) starts at ESA's level plus the bridge and then follows GIPL's rise. GIPL's start-up years (2021–2025) are
shown in blue for reference only. The Fairbanks test area has fewer cells because GIPL's stuck cells are excluded.

---

## Recommendation: the delta change method

For each 1 km cell, model and scenario:

> **future surface temperature (era) = ESA GST 2014–2023 + bridge + GIPL change**
>
> - **ESA GST 2014–2023:** today's observation-based level.
> - **bridge:** the air warming the same climate models project from 2014–2023 to 2026–2035 (≈ +1 °C). GIPL cannot
>   supply this itself because of its start-up period.
> - **GIPL change:** GIPL surface temperature in the era minus GIPL 2026–2035.

- **What we keep from GIPL:** how much the ground surface warms. This trend includes information about vegetation, snow, and soil characteristics that have been "baked in" to the GIPL model.
- **What we drop:** GIPL's own temperature levels. They run about
  1.2 °C colder than ESA (section 2), so we needed to adjust them to avoid having the future ground surface temperature be colder than the observed (not realistic).
- **Where it cannot be used:** GIPL stuck cells and the 2 km border around them (~9 % of permafrost cells). These areas need to be interpolated, filled with values from a similar dataset, or flagged as NA.


## Caveats

- ESA CCI is model-based too (satellite surface temperature driving a permafrost model), not direct measurement.
- The method assumes GIPL's *changes* are right even where its *levels* are off. We cannot test that directly.
- The bridge uses air warming as a stand-in for surface warming over about 12 years.
- 5-model average only.

<sub>Methods: 1 km GIPL grid; ESA sampled at cell centres; air temperature = SNAP 2 km 5-model average (parent cell).
Jumps measured after removing the model air warming between the two reference periods. Scripts:
`scripts/02_tests/t3_esa_gipl_continuity.py` (test areas), `scripts/02_tests/t3_surface_splice.py` (statewide), `scripts/03_report/splice_schematic.py` (example-cell schematic), `scripts/03_report/splice_levels_vs_changes.py` (levels vs warming figure);
tables in `<data>/results/t3/splice_methods.csv`.</sub>
