# GIPL 2.0 (1 km), issue 2: start-up period and temperature levels
## Can GIPL ground temperatures be read as absolute values, or only as a change?

**Question:** should GIPL's projected ground temperatures be used as **absolute values** (for example, frozen vs
thawed around 0 °C), or only for their **change** over time (how much the ground warms)?

This matters because one proposed index design sorts cells around the freezing point. Simplified, it reads:
**−1 °C and below = good, −1 to 0 °C = moderate, above 0 °C = bad** (called the **0 °C scheme** below). That only works
if GIPL's temperatures are right in absolute terms. The alternative, used in V2 of [PTI.md](PTI.md), takes only
GIPL's change and gets today's level from ESA CCI.

**Revised 2026-10-26.** GIPL's year labels turned out to be 20 years late ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)): the
file labelled 2021 holds the climate of 2001. The first version of this document compared GIPL with observations 20
years apart and reported a cold bias of 1.2–2 °C. With the years matched, most of that bias disappears. All years
below are **climate years** (file year − 20).

---

**Short answer:**
- **On average, GIPL's levels are close to the observation-based values once the years are matched.** In 2004–2015,
  when GIPL and ESA were both driven by observed weather, GIPL is **within 0.2 °C of ESA at 1 m and 2 m** and
  **0.9 °C warmer at the surface** (statewide median). Against 90 monitoring boreholes, GIPL's median error is
  −0.3 / −0.5 / −0.05 °C at the surface / 1 m / 2 m, comparable to ESA's (−0.5 / +0.3 / +0.4 °C).
- **Cell by cell, the two still differ a lot:** the middle 80 % of cells spans about −1.5 to +1.9 °C at 1 m. GIPL also
  compresses the range: it is warmer than ESA where the ground is very cold and colder where ESA puts the ground
  above 0 °C (by 1.4–2.1 °C at 1 m where ESA shows +1 to +3 °C).
- **Below the surface, GIPL's 0 °C line is about right.** Against ~2,800 field sites where permafrost was or was not
  found (CUSP), the temperature that best separates the two groups at 1 m is −0.2 °C in GIPL (ESA: +1.4 °C). Both
  datasets rank the sites equally well. At the surface, neither dataset's 0 °C line works (best splits +1.7 to
  +2.3 °C).
- **The 0 °C scheme on raw GIPL is possible below the surface, but fragile.** At mid-century (2051–2080), half of all
  cells sit within 0.5 °C of a class edge at 1 m and 2 m: thawing ground holds near 0 °C while its ice melts. Cell-level
  differences of ±1.5 °C are enough to move many cells between classes.
- **GIPL's first years are explained.** 2001–2003 is a start-up period (the ground below the surface starts far too
  cold and climbs about 2 °C). 2001–2015 is driven by observed weather in every run, which is why runs that should
  differ were identical through "2035" in the files. Scenario-specific behaviour starts in 2016.
- **The change signal behaves sensibly:** GIPL's surface warms 0.8–0.9 times as fast as the projected air under both
  scenarios (0.5–0.7 times at 1–2 m) and passes on 74 % of the extra RCP 8.5 warming by 2081–2100.
- **Recommendation:** keep **change only (PTI V2)** for the index: it needs no fixed temperature line and keeps ESA's
  observation-based level. If the team wants a temperature-threshold scheme, raw GIPL at 1–2 m is now a candidate,
  but its class edges should be checked against field data, and the pile-up near 0 °C makes classes unstable.

---

## Key terms, in plain language

- **Level (absolute value):** the temperature itself, e.g. −1.5 °C. **Change:** how much it rises between two periods,
  e.g. +2.0 °C.
- **MAGT:** mean annual ground temperature. GIPL provides it at the ground surface and at fixed depths (0.5 m, 1 m,
  2 m, ...).
- **Climate year:** the year whose climate a GIPL file carries: file year − 20 (− 19 for GFDL-CM3 RCP 8.5;
  [GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).
- **Offset:** GIPL minus another dataset for the same cells and the same years. **Bias:** a systematic offset, i.e.
  one that does not average out.
- **ESA-adjusted (delta change method):** ESA's level for 2014–2023 + GIPL's change from 2014–2023. GIPL contributes
  only its change ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)).
- **Start-up period:** a model's first years after it starts, while it is still settling.
- **Borehole:** a monitored hole with temperature sensors at fixed depths; here, the University of Alaska Fairbanks
  (UAF) Permafrost Laboratory network.
- **CUSP:** the CommUnity near-Surface Permafrost dataset: field records (probes, pits, cores) of whether permafrost
  was found in the top metre or two.
- **Ranking skill:** the chance that a randomly chosen permafrost site is colder in a dataset than a randomly chosen
  site without permafrost (0.5 = no better than a coin toss, 1 = perfect). It measures whether the *pattern* is right,
  independent of the level.
- **Zero curtain:** thawing frozen ground stays close to 0 °C while its ice melts, because melting absorbs the heat.

## Data

| | What | Years used | Role here |
|---|---|---|---|
| **GIPL 2.0** (SNAP) | modelled MAGT at the surface, 0.5 m, 1 m, 2 m; 1 km | climate years 2001–2100 (files 2021–2120) | the dataset being tested; 5-model average (headline), GFDL-CM3, NCAR-CCSM4; RCP 4.5 and 8.5 |
| **ESA CCI Permafrost v5** | satellite surface temperature + permafrost model; ground surface (GST), 1 m, 2 m; 1 km | 2003–2023 | observation-based reference (no 0.5 m layer) |
| **Air temperature** (SNAP 2 km) | CRU TS 4.08 (observed) and CMIP5 5-model average (projections) | 2003–2100 | the weather GIPL was driven by; warming rates |
| **Boreholes** (UAF Permafrost Lab, Arctic Data Center) | daily measured temperatures, 121 Alaska sites | 2015–2025 | independent check of levels |
| **CUSP v1.2** | field records of permafrost found / not found, 2,802 GIPL cells | 2002–2024 | independent check of frozen / thawed calls |

Cells: permafrost cells where GIPL behaves normally (724,326 cells; GIPL's stuck cells and the 2 km border around them
are excluded, see [GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)). Following the team's choice, 0.5 m is analysed for start-up,
change and the 0 °C scheme only; ESA has no 0.5 m layer to compare levels with.

---

## 1. GIPL's first fifteen years

### 1.1 What the runs look like

![GIPL 2001–2050 at four depths, three runs, two scenarios](figures/gipl2_startup.png)

*Statewide median of permafrost cells, on climate years. Dark band: start-up years; light band: observed weather,
the same in every run. The orange GFDL-CM3 line is hidden under the blue 5-model average line until 2015: the two
are identical.*

- **Below the surface, GIPL starts far below its later values and climbs fast.** At 1 m, the 5-model average under
  RCP 4.5 goes from −3.7 °C in 2001 to −1.9 °C in 2003; at 2 m from −4.0 to −2.2 °C. The surface rises from −1.9 to
  −0.3 °C over the same two years. Real ground does not warm 1.5–2 °C in two years: the model starts from a
  steady-state ground profile and needs about three years to settle. **2001–2003 should not be used.**
- **From 2004 to 2015, GIPL follows observed weather.** Its year-to-year ups and downs match the observed air
  temperature (median correlation per cell 0.76). For example, the surface drops about 1 °C in 2006, a cold year
  (observed air −1.3 °C from 2005).
- **The NCAR-CCSM4 run jumps in 2003** (surface +3.6 °C under RCP 4.5 and +5.1 °C under RCP 8.5, against −0.3 °C in
  the other runs), then drops back. Neither observed nor projected air temperature shows a matching warm year. The
  NCAR-CCSM4 runs match no climate data we could find ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md), section 5).

### 1.2 The two scenarios start from different ground

![Gap between RCP 8.5 and RCP 4.5, year by year](figures/gipl2_scenario_gap.png)

Through 2015 both scenarios carry the same observed weather, so GIPL's two runs should be identical, unless they
started from different ground temperatures.

| Median gap, RCP 8.5 vs RCP 4.5 (5-model average) | Surface | 0.5 m | 1 m | 2 m | Air |
|---|---|---|---|---|---|
| 2001 | 0.53 °C | 1.02 °C | 1.33 °C | **1.71 °C** | 0 (same observed weather) |
| 2003–2015 | ≤ 0.07 °C | 0.11–0.18 °C | 0.11–0.22 °C | 0.11–0.29 °C | 0 |
| 2016–2022 | 0.37–1.23 °C | 0.28–0.81 °C | 0.25–0.70 °C | 0.21–0.58 °C | 0.08–0.85 °C |

- **In 2001 the two runs are 0.5–1.7 °C apart, more at depth**, although their weather is identical: they were
  started from different ground temperatures. The difference fades by 2003 at the surface and shrinks to about
  0.1–0.3 °C below it.
- **Four of the six runs start from exactly the same ground**: in 2001 the 5-model average and GFDL-CM3 under RCP 4.5
  and NCAR-CCSM4 under both scenarios are identical in every cell, at the surface and at 1 m. Why the two other RCP 8.5
  runs start elsewhere is unexplained.
- **From 2016 the gap opens** as each scenario follows its own projected weather.

### 1.3 Why several runs share one weather sequence

The first version of this document found that through "2035" (in the files) several runs shared one weather sequence.
With the years shifted, the reason is simple:
- **2001–2015 is observed weather, the same in every run.** GFDL-CM3 RCP 4.5 and the 5-model average RCP 4.5 also
  start from the same ground, so they are identical in every cell through 2015.
- **GFDL-CM3 RCP 8.5 is one year further along** (file year − 19): it carries the same observed sequence, one file
  year earlier.
- **From 2016, each run follows its own climate model's air temperature**: year-to-year match 0.94–0.95 per cell for
  GFDL-CM3, 0.56–0.57 for the 5-model average (whose air temperature swings less), NCAR-CCSM4 unknown
  ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).

**What this means:** apart from the start-up years (2001–2003), GIPL's early years are usable. In 2004–2015 they
describe real observed years and can be compared with observations year for year. From 2016 they describe projected
weather, so only multi-year means can be compared with observations.

## 2. GIPL vs ESA for the same years

GIPL and ESA, both 2004–2015: years when both were driven by observed weather.

![GIPL minus ESA by depth and region](figures/gipl2_bias_depth.png)

| GIPL − ESA, median (2004–2015, RCP 8.5) | Surface (vs ESA GST) | 1 m (vs ESA T1m) | 2 m (vs ESA T2m) |
|---|---|---|---|
| Statewide | **+0.9 °C** | **−0.1 °C** | **−0.2 °C** |
| Arctic | +1.0 °C | +0.3 °C | +0.2 °C |
| Interior | +0.7 °C | −0.4 °C | −0.4 °C |
| West | +0.8 °C | −0.2 °C | −0.2 °C |
| South | +1.1 °C | 0.0 °C | −0.1 °C |
| Cells where GIPL is colder | 24 % | 53 % | 57 % |
| Spread, statewide (10th to 90th percentile) | −0.7 to +2.5 °C | −1.5 to +1.9 °C | −1.6 to +1.8 °C |

RCP 4.5 is within 0.1 °C (both scenarios carry the same observed weather).
- **Below the surface, GIPL is close to ESA on average** (within a few tenths of a degree statewide and in every
  region).
- **At the surface, GIPL is about 0.9 °C warmer.**
- **It holds in every run:** GFDL-CM3 +0.9 / −0.1 / −0.2 °C, NCAR-CCSM4 +1.4 / +0.2 / +0.1 °C (surface / 1 m / 2 m).
- **Over 2014–2023, the reference decade of the delta change method**, the offsets are +0.1 / −0.6 / −0.5 °C (RCP 4.5)
  and +0.6 / −0.2 / −0.2 °C (RCP 8.5). Eight of those ten GIPL years are projected weather, not the real years.
- **It is not one number:** cells differ by about 3 °C between the 10th and 90th percentiles, so no single correction
  fixes it ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md), section 3).
- **GIPL compresses the range.** At 1 m (2014–2023), GIPL is warmer than ESA where ESA shows very cold ground
  (+0.7 to +2.2 °C below −6 °C), within about ±0.3 °C between −6 and 0 °C, and colder where ESA puts the ground above
  0 °C (−0.7 °C at 0 to +1 °C, −1.4 to −2.1 °C at +1 to +3 °C). The second part matters most for a 0 °C scheme.

![GIPL minus ESA maps](figures/gipl2_bias_maps.png)

*2004–2015, RCP 8.5. Blue: GIPL colder than ESA; red: warmer.*

## 3. Two independent field checks

ESA is also model-based, so the comparison above cannot say on its own which dataset is off. Two kinds of field data
can.

### 3.1 Boreholes: measured ground temperatures

![Boreholes: ESA and GIPL against observed temperatures](figures/gipl2_boreholes.png)

90 borehole sites in normal GIPL cells, with 1–18 years of daily data each (mostly 2015–2024; two sites back to
2007). For each site, the observed mean annual temperature is compared with ESA and with GIPL for the same years.

| Error = dataset − observed (median of sites) | Surface (84 sites) | 1 m (65 sites) | 2 m (23 sites) |
|---|---|---|---|
| ESA CCI | −0.5 °C | +0.3 °C | +0.4 °C |
| GIPL, same years (RCP 8.5) | **−0.3 °C** | **−0.5 °C** | **−0.05 °C** |
| GIPL, same years (RCP 4.5) | −0.8 °C | −0.7 °C | −0.3 °C |
| Sites where GIPL (RCP 8.5) is colder than observed | 56 % | 65 % | 57 % |
| Typical size of the error (mean absolute): ESA / GIPL | 1.9 / 1.5 °C | 1.3 / 1.2 °C | 1.0 / 1.0 °C |

- **Neither dataset runs consistently cold or warm at the boreholes:** both medians are within about half a degree,
  and GIPL's typical site error is no larger than ESA's.
- **Most borehole years (2016–2024) are projected years in GIPL**, so GIPL's weather in those years is not the real
  weather; the two scenarios differ by up to 0.5 °C here for that reason. Only multi-year means are comparable.
- **ESA is not perfect either:** a single site typically differs from its 1 km cell by 1–2 °C (last row). At the
  surface, ESA runs 2–4 °C too cold at a cluster of North Slope and Brooks Range sites (Deadhorse, Franklin Bluffs,
  Imnavait, Roche Moutonnée), and too warm at recently burned sites. Both datasets are accurate on average, not at
  every point.

### 3.2 CUSP: was permafrost found?

![Permafrost found vs not found, against ESA and GIPL temperatures](figures/gipl2_cusp.png)

2,802 GIPL cells with field records from 2002 on: 1,375 where permafrost was found in at least half of the records
and 1,427 where it mostly was not (searches reaching at least 1 m). For each cell, the dataset temperature for the
years of the field visits is compared with what was found. (In the histograms, cells colder than −8 °C are shown at
−8 °C.)

| | Ranking skill | At a 0 °C split: permafrost sites read as thawed | At a 0 °C split: no-permafrost sites read as frozen | Best split |
|---|---|---|---|---|
| ESA, surface | 0.82 | 48 % | 10 % | +1.7 °C |
| ESA, 1 m | 0.84 | 39 % | 15 % | +1.4 °C |
| ESA, 2 m | 0.84 | 33 % | 17 % | +1.3 °C |
| GIPL, surface | 0.81 | 58 % | 7 % | +2.3 °C |
| GIPL, 0.5 m | 0.81 | 31 % | 23 % | −0.2 °C |
| GIPL, 1 m | 0.81 | **25 %** | **31 %** | **−0.2 °C** |
| GIPL, 2 m | 0.82 | 18 % | 39 % | −0.2 °C |

- **Both datasets rank places about equally well** (ranking skill 0.81–0.84).
- **Below the surface, GIPL's 0 °C line is about right:** its best split is −0.2 °C at 0.5, 1 and 2 m. At 0 °C, GIPL
  misreads about a quarter to a third of each group at 1 m; ESA misreads more permafrost sites (39 %) and fewer
  no-permafrost sites (15 %).
- **ESA's 0 °C line is too low** (best split +1.3 to +1.7 °C). Many 1 km cells whose average temperature is above 0 °C
  still contain permafrost in places (north-facing slopes, peat, under insulating moss).
- **At the surface, neither works with 0 °C** (best split +1.7 °C in ESA, +2.3 °C in GIPL): snow keeps the surface
  warmer than the ground below.
- **Under the 0 °C scheme**, sites without permafrost would be rated at 1 m as follows:

  | No-permafrost sites | ≤ −1 °C (good) | −1 to 0 °C (moderate) | > 0 °C (bad) |
  |---|---|---|---|
  | ESA | 7 % | 12 % | 81 % |
  | GIPL | 9 % | 22 % | 69 % |

  Few places where field crews found no permafrost would be rated "good" by either dataset.

## 4. What the 0 °C scheme would do at mid-century

The scheme applied to GIPL in 2051–2080, two ways: to GIPL's raw values, and to ESA-adjusted values (ESA level +
GIPL change from 2014–2023).

![Classes at 1 m, raw vs ESA-adjusted, and class shares by depth](figures/gipl2_classes_mid.png)

| 2051–2080, statewide, RCP 4.5 / RCP 8.5 | Surface | 1 m | 2 m |
|---|---|---|---|
| Same class, raw vs adjusted | 89 / 82 % | **66 / 77 %** | **59 / 71 %** |
| Raw GIPL in a colder class | 5 / 2 % | 29 / 15 % | 36 / 21 % |
| "Moderate" (−1 to 0 °C), raw GIPL | 7 / 11 % | 27 / 19 % | 35 / 26 % |
| "Moderate" (−1 to 0 °C), adjusted | 5 / 7 % | 8 / 7 % | 10 / 9 % |
| Raw values within 0.5 °C of a class edge | 16 / 23 % | 49 / 44 % | 55 / 52 % |

0.5 m (raw only): 38 / 29 % good, 22 / 14 % moderate, 40 / 57 % bad.
- **At 1 m and 2 m, raw and adjusted GIPL agree for 59–77 % of cells.** Where they differ, raw GIPL is mostly in the
  colder class: it holds warm ground near 0 °C where ESA is above it (section 2). In the Interior they agree for
  50 % (RCP 4.5) and 75 % (RCP 8.5) of cells at 1 m.
- **The surface agrees better (82–89 %)** because most surface values are well away from the class edges: most Arctic
  cells stay below −1 °C and most of the rest of the state is above 0 °C.

![GIPL values pile up just below 0 °C below the surface](figures/gipl2_pileup.png)

- **Below the surface, GIPL's values pile up just under 0 °C.** Thawing frozen ground has to melt its ice first, which
  holds the temperature close to 0 °C for years (the zero curtain). At 1 m and 2 m, about half of all cells sit
  between −1.5 and +0.5 °C at mid-century (55–79 % in the Interior).
- **Inside that pile-up, a 1 °C-wide class is unstable.** A few tenths of a degree, well within the cell-level
  differences in section 2, move a cell between classes.

## 5. Is the change signal any better?

**What the change fixes:**
- **Cell-level offsets drop out.** GIPL's change between two periods does not depend on its level, so the ±1.5 °C
  cell-to-cell differences from ESA have no effect.
- **GIPL's pattern is sound** (section 3.2): both datasets rank places equally well.
- **The reference decade is now clean:** GIPL's change is measured from 2014–2023, the same decade as ESA's level, so
  no air-temperature bridge is needed ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)).

**What to keep in mind:**

1. **GIPL's surface warms less than the air.** Over 2036–2070, GIPL's surface warms 0.27 (RCP 4.5) and 0.73 (RCP 8.5)
   °C per decade against 0.29 and 0.90 for the projected air: 0.8–0.9 times as fast under both scenarios (0.5–0.7
   times at 0.5–2 m). By 2081–2100, 74 % of the extra RCP 8.5 air warming reaches GIPL's surface and 42–49 % reaches
   0.5–2 m. So GIPL follows the scenarios, but damped. This is the main reason PTI V2 is lower than V1
   ([PTI.md](PTI.md), section 2).
2. **The recent record points the other way.** Over 2003–2023, ESA's ground surface warmed 1.7 times as fast as the
   observed air (0.62 vs 0.37 °C per decade). Whether the ground will lag the air (GIPL) or not cannot be tested
   before it happens.
3. **The reference decade mixes observed and projected years.** GIPL's 2014–2023 contains two observed years
   (2014–2015) and eight projected ones. That barely changes GIPL's own warming (by less than 0.1 °C against a
   2016–2025 reference), but it moves the comparison with air warming by about 0.2 °C.
4. **Below the surface, the change stalls near 0 °C.** In the pile-up (section 4), warming at 1 m and 2 m slows while
   ice melts. Depth-based change therefore understates warming in thawing cells. The surface does not have this
   problem, which is one reason PTI V2 uses the surface.

## 6. The options side by side

| | Raw GIPL values, 0 °C scheme | **A.** ESA-adjusted values, 0 °C scheme | **B.** Change only (PTI V2) |
|---|---|---|---|
| Uses from GIPL | level and change | change | change |
| Today's level comes from | GIPL | ESA | ESA (in 2 °C-wide bands) |
| Affected by GIPL's level offsets (statewide within 0.2 °C at 1–2 m, +0.9 °C at the surface; ±1.5 °C cell to cell) | fully | no | no |
| Is 0 °C the right line at 1 km? | yes below the surface (best split −0.2 °C); no at the surface (+2.3 °C) | no: ESA's best split is +1.3 to +1.7 °C | does not rely on a fixed temperature line |
| A 1 °C level error can move a cell | a full class | a full class | at most one "today" band (2 °C wide); warming bands unaffected |
| Field check, 1 m, at 0 °C | 25 % of permafrost sites read thawed, 31 % of no-permafrost sites read frozen | 39 % / 15 % (ESA) | not testable directly (future change) |
| Stability near the class edges | half of 1–2 m cells within 0.5 °C of an edge | same pile-up, shifted by ESA's level | warming bands 1 °C wide; edges matter at 2 °C (PTI.md) |
| **Verdict** | **possible below the surface, with field-checked edges** | possible only with calibrated edges | **recommended for the index** |

---

## Recommendation

1. **Use GIPL for its change (as in PTI V2) in the index.** It keeps ESA's observation-based level, needs no fixed
   temperature line, and is not affected by GIPL's cell-level offsets.
2. **GIPL's levels below the surface are usable as rough absolute values** (statewide within a few tenths of a degree
   of ESA and the boreholes, and a 0 °C line close to the best split at the CUSP sites), but not at the surface, and not
   cell by cell without caution.
3. **If the team wants a temperature-threshold scheme**, raw GIPL at 1–2 m or ESA-adjusted values are both candidates.
   Set the class edges from field data (for example CUSP) rather than at −1 and 0 °C, and expect many cells near the
   edges.
4. **Always read GIPL on climate years** (file year − 20; GFDL-CM3 RCP 8.5: − 19), and skip 2001–2003.
5. **Report to SNAP** the 20-year label shift, the identical runs through 2015 (shared observed weather), the
   duplicated final year of GFDL-CM3 RCP 8.5, and the unidentified forcing of the NCAR-CCSM4 runs
   ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).

## Caveats

- **ESA CCI is model-based** (satellite surface temperature driving a permafrost model), not measurement.
- **The 20-year shift is inferred from the data**, not documented ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).
- **A borehole is a point; a GIPL or ESA cell is 1 km².** Individual sites can differ from their cell by several
  degrees (snow drifts, vegetation, water, recent fire). The medians over many sites are the meaningful numbers.
  Boreholes in GIPL's stuck cells or their border (25 sites, mostly in the eastern Interior) are excluded.
- **CUSP sites are not spread evenly:** most no-permafrost cells are in the West and Interior, most permafrost cells
  in the Arctic and Interior. "No permafrost" means none was found within the depth searched (at least 1 m), not that
  there is none deeper or nearby.
- **From 2016, GIPL's weather is projected**, so comparisons with observations after 2015 use multi-year means only.
- **5-model average throughout**, with GFDL-CM3 and NCAR-CCSM4 checked for the start-up and levels.

<sub>Methods: GIPL 2.0 source GeoTIFFs (SNAP CKAN archive; identical to Rasdaman), 1 km grid, read on climate years
(file year − 20; GFDL-CM3 RCP 8.5 − 19; [GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)); cells with ESA CCI PFR > 0 (2023) and
normal GIPL behaviour (class 2 of the stuck-cell mask, 724,326 cells); regions from the USDA general soil map
physiography ([CORRELATION.md](CORRELATION.md)). ESA sampled at cell centres (nearest 0.01° pixel), 2003+ only for
trends (one product version). Air temperature: CRU TS 4.08 (observed, to 2015) and SNAP 2 km 5modelAvg (projected,
from 2016), parent 2 km cell. Offset = GIPL − ESA, same years, per cell. Year-to-year correlations: per cell, Pearson
correlation of first differences, median over every 10th cell. Boreholes: "Thermal State of Permafrost in North
America – continuously observed ground temperatures" (UAF Permafrost Laboratory, Arctic Data Center, 2015/16–2024/25
packages; 121 US sites); June–May years with ≥ 330 valid days per sensor; surface = "surf" sensor (else 0–5 cm), 1 m
and 2 m from a sensor within 5 cm or linear interpolation between sensors ≤ 1.5 m apart; site means over all usable
years; ESA and GIPL for the two calendar years each June–May year spans. CUSP v1.2
(https://github.com/jonschwenk/cusp): Alaska records, visual classifications dropped, "not found" only with a search
depth ≥ 100 cm; grouped by GIPL cell (permafrost cell = permafrost found in ≥ 50 % of records); dataset values averaged
over the median visit year ± 2 years (GIPL from 2004 only). Ranking skill = area under the ROC curve; best split =
threshold maximising the mean of the two hit rates. 0 °C scheme: ≤ −1, −1 to 0, > 0 °C (simplified team proposal).
Scripts: `scripts/01_data/fetch_boreholes.py`, `scripts/02_tests/t6_gipl_levels.py` (stacks, start-up, levels,
scenario response, classes, trends), `scripts/02_tests/t6b_sites.py` (boreholes, CUSP),
`scripts/03_report/gipl_issue2_figures.py`; `slurm/17_t6_prep.slurm`, `slurm/18_t6_analyze.slurm`; tables in
`<data>/results/t6/`. Shared-weather and forcing tests: `scripts/02_tests/t7_gipl_forcing.py`
([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).</sub>
