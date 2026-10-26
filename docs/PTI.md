# Permafrost Thaw Index (PTI)
## "How susceptible to thaw is the permafrost in this cell, if permafrost is there?"

That question defines the index. It describes the permafrost **in a 1 km cell, if permafrost is there**: how close
the ground is to thawing today and how much it is projected to warm.

---

**BLUF:**
- **The index comes from a simple two-way table:** how warm the ground surface is today and how much it is
  projected to warm. Each cell's class can be explained in one sentence ("surface near 0 °C today, projected to warm
  +3.3 °C: High").
- **Why a table:** a scale based only on future temperature asks just one question: how warm will this place be? That
  makes very cold places look safe even when they warm a lot, and warm places look at risk even when little changes.
  The table asks two questions instead (how warm is it today, and how much will it warm?), and its rules are written
  out so anyone can check or adjust them.
- **Through 2050, almost no cell is High** (warming mostly stays under 2 °C). Under RCP 8.5, about two-thirds of
  permafrost cells are High by 2051–2080 (60–69 %) and nearly all by 2081–2100 (94–100 %). Under RCP 4.5 the answer
  depends on the version (next point).
- **Two versions, differing only in where the projected warming comes from:** V1 uses air temperature (no GIPL); V2
  uses GIPL, with air temperature where GIPL has no usable values (about 1 in 5 Interior cells, flagged). **GIPL's
  ground surface warms about 20 % less than the air**, and much of the Interior, West and South sits close to the
  2 °C warming edge at mid-century. So the versions often disagree: under RCP 4.5 in 2051–2080, V1 rates 65 % of
  permafrost cells High and V2 16 %. Where they differ, V2 is almost always one class lower (sections 2 and 4).
- **Permafrost extent, terrain and land cover stay out of the number** and go in the data sentence.
- **Decisions needed:** whether to adopt V1 or V2 (now the most consequential choice), and the table's entries and
  band edges (especially the 2 °C warming edge, and the "over 5 °C" column, which decides much of the Arctic under
  RCP 8.5 by 2081–2100).

---

## Caveats

It is important to note that our 1km resolution datasets cannot disambiguate permafrost vs non-permafrost areas within the same cell. Every value (e.g. MAAT, MAGT) is therefore some combination of permafrost and non-permafrost areas, where they exist.

What we **cannot** answer:
- "how much of the cell has permafrost?"
- "where in the cell is the permafrost?"
- "what specific hazards could result from permafrost thaw in this cell (e.g. thermokarst)?"
- "what is the temperature of the permafrost in this cell?"

We simply do not have the data required to make predictions on those topics. However, those topics can be contextualized next to the index in a **data sentence** describing datasets not directly used in computing the index. For example, the following data sentence leads with the index value for the cell, followed by higher-resolution contextual information about the cell:

> *PTI: ![High](figures/badges/pti_high.svg) (2051–2080, RCP 8.5): surface near 0 °C today (−1.0 °C), projected to
> warm +3.2 °C. Permafrost extent: sparse (PFR 29 %). Terrain: 45 % sun-facing slopes, so permafrost is likely
> limited to shaded and flatter ground. Land cover: 60 % black spruce / wetland (insulating organic layer).*

Section 5 of this document has example data sentences for 3 test areas.


---

## Key terms

- **PTI class:** one of three classes, coloured as in the table: ![Low](figures/badges/pti_low.svg)
  ![Moderate](figures/badges/pti_moderate.svg) ![High](figures/badges/pti_high.svg).
- **Permafrost cells:** 1 km cells where ESA shows any permafrost (permafrost fraction, PFR, above 0; ≈ 800,000
  cells). Only these cells get a class.
- **Today's surface temperature:** mean annual ground surface temperature, 2014–2023, from ESA CCI Permafrost
  (observation-based).
- **Projected warming:** how much the ground surface warms from today (2014–2023) to an era (2026–2050, 2051–2080,
  2081–2100), under a greenhouse-gas scenario (RCP 4.5: moderate; RCP 8.5: high), using the 5-climate-model average.
- **Delta change method:** future = today's observed level + the change a model projects; the model contributes only
  its change ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)).
- **V1:** projected warming = air-temperature warming (SNAP 2 km downscaled climate). No GIPL.
- **V2:** projected warming = GIPL ground-surface warming (delta change method). GIPL's files are labelled 20 years
  late, so V2 reads each era from the files labelled 20 years later ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)). Where GIPL
  has no usable values ([GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)), V1's air warming is used and the cell is flagged.
- **Context layers:** permafrost extent (ESA PFR), terrain (share of sun-facing and shaded slopes) and land cover
  (share of black spruce / wetland). Shown in the data sentence, not used in the class.

---

## 1. How the index works: the two-way table

Each permafrost cell is described by two numbers, and the table turns them into a class:
1. **Today's surface temperature**, in four bands: cold (below −4 °C), cool (−4 to −2 °C), near 0 (−2 to 0 °C),
   warm surface (above 0 °C).
2. **Projected warming** by the era, in five bands: under 2 °C, 2–3 °C, 3–4 °C, 4–5 °C, over 5 °C.

![The two-way table](figures/t4_table.png)

- Going **right** (more warming), the class rises; going **down** (warmer today), it rises too.
- The **warm-surface row** is not automatically High: permafrost under a surface that is already above 0 °C
  survives only where it is locally protected (snow, organic layers, shading), so it stays Moderate while warming is
  under 2 °C.
- With three classes, the **near-0 and warm-surface rows are identical** (Moderate under 2 °C of warming, High above).
  Most of the Interior, West and South is in these two rows, so for them **the 2 °C edge alone decides the class**.
- The **over 5 °C** column is the 4–5 °C column moved up one class (High stays High), so it changes only the cold row.
  It matters for the Arctic under RCP 8.5 by 2081–2100: its surface warms by 5–6 °C (median) and ends above 0 °C,
  so cells that are cold today become High rather than Moderate.
- The entries are a **draft for the team to edit**; maps and numbers follow the table. (An earlier draft had five
  classes; Very low and Low are now Low, High and Very high are now High.)
- Permafrost extent, terrain and land cover describe *how much* of a cell is permafrost and *where*, which the index
  does not answer; ground temperature and permafrost fraction also largely carry the same information
  ([CORRELATION.md](CORRELATION.md)). They are reported in the data sentence instead.

## 2. Two versions: V1 and V2

### Why two versions

The index needs to know how much the **ground surface** will warm. There are two sources for that, and each has a
weakness:

- **Air temperature projections** (SNAP 2 km downscaled climate, 5-model average) cover every cell and are simple to
  explain. But air is not ground: snow, vegetation and organic soil sit between the two, so air warming is only a
  stand-in for ground-surface warming. **V1** uses air warming.
- **GIPL** is a permafrost model that turns air temperature and snow into ground temperatures, so its surface
  temperature is closer to what the ground itself experiences. But it has areas with unusable values
  ([GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)), and its temperature levels differ from today's observation-based values cell
  by cell (by up to about 2 °C), so only its *change* is used ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)). **V2**
  uses GIPL's warming where it is usable and air warming elsewhere (flagged).

Neither can be checked against future observations, so both are shown; which one to adopt is an open question.

| | Projected warming from | Uses GIPL | Cells with a class: all of Alaska | Cells with a class: Interior |
|---|---|---|---|---|
| **V1** | air temperature (SNAP 2 km, 5-model average) | no | 100 % | 100 % |
| **V2** | GIPL ground surface (delta change method); air temperature where GIPL has no usable values, flagged | yes | 100 % (GIPL in 91 %) | 100 % (GIPL in 81 %) |

Both use the same today's surface temperature and the same table.

### GIPL's ground surface warms less than the air

<img src="figures/t4_gipl_minus_air.png" alt="Where GIPL's surface warming differs from air warming" width="55%">

*V2 − V1 projected warming, 2051–2080, RCP 8.5. Blue: GIPL's ground surface warms less than the air; red: more.*

- **Almost everywhere, GIPL's surface warms less than the air:** by about 0.5–0.8 °C statewide at mid-century, about
  a fifth of the air warming, and by up to 1.4 °C in the West and South by 2081–2100 under RCP 8.5. Only along the
  eastern Brooks Range does it warm more.
- **Part of the gap is the reference decade.** GIPL's 2014–2023 contains two observed, unusually warm years
  (2014–2015) before its projections start. Measured from 2016–2025 instead, the gap shrinks by about 0.2 °C.
- **The rest is GIPL's own ground response.** Over 2016–2070, GIPL's surface warms 0.8–0.9 times as fast as the
  projected air under both scenarios: snow, vegetation and soil sit between the air and the ground.
- **Snow alone does not explain the pattern.** The air warms about twice as much in winter as in summer, but cells
  where winter warming dominates do not lag much more (Spearman ρ −0.05 to −0.08 statewide, −0.3 to −0.4 in the
  Arctic). GIPL's snow and soil inputs are not documented, so the causes cannot be separated.
- **The recent record points the other way.** Over 2003–2023, ESA's observation-based ground surface warmed *faster*
  than the observed air (0.62 vs 0.37 °C per decade). Whether the ground will lag the air (GIPL) or keep pace with it
  (V1) cannot be tested before it happens.

| 2051–2080, RCP 4.5 / RCP 8.5 | Winter air warming | Summer air warming | V2 − V1 (annual ground surface) |
|---|---|---|---|
| Statewide | +3.6 / +4.4 °C | +1.7 / +2.6 °C | −0.6 / −0.8 °C |
| Arctic | +4.1 / +5.3 °C | +1.7 / +2.8 °C | −0.5 / −0.7 °C |
| Interior | +3.2 / +3.9 °C | +1.6 / +2.5 °C | −0.5 / −0.7 °C |
| West | +3.7 / +4.6 °C | +1.7 / +2.5 °C | −0.8 / −1.0 °C |
| South | +2.7 / +3.1 °C | +1.8 / +2.6 °C | −0.6 / −0.9 °C |

Because a difference of half a degree can move a cell across a warming band, V1 and V2 often give different classes,
most of all at mid-century, when much of Alaska's projected warming sits close to the 2 °C edge. Section 4 maps where
they differ. Each area in section 3 lists its own median warming for V1 and V2.

## 3. Results, area by area

Each subsection covers one area, so it can be discussed on its own: **statewide** first, then the four regions
(**Arctic, Interior, West, South**), taken from the physiographic regions of the USDA general soil map (map in
[CORRELATION.md](CORRELATION.md)).

Each area has two figures, one per scenario. **Rows are eras; columns are V1 (table, map) and V2 (table, map).**

How to read a table panel:
- The coloured boxes are the two-way table, drawn on temperature axes (today's surface temperature down the side,
  projected warming along the bottom; dotted lines = band edges).
- Grey shading shows where the area's cells sit (darker = more cells). The histograms on the edges show the spread
  of today's temperature (right) and of projected warming (top).
- The percentage in each box is the share of the area's permafrost cells that fall in it.

Maps show the same classes. On the regional maps, permafrost cells outside the region are light grey.

Each area's table gives the median projected warming and the share of its permafrost cells per class, as
**V1 / V2**.

### 3.1 Statewide

799,669 permafrost cells; today's surface temperature: median −0.1 °C. V2 uses GIPL in 91 % of cells (air warming,
flagged, in the rest).

![Statewide, RCP 4.5](figures/pti_statewide_rcp45.png)

![Statewide, RCP 8.5](figures/pti_statewide_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.5 / +1.2 °C | 34 / 34 % | 66 / 66 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.4 / +1.0 °C | 34 / 34 % | 66 / 66 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.5 / +2.0 °C | 25 / 28 % | 10 / 56 % | 65 / 16 % |
| 2051–2080, RCP 8.5 | +3.5 / +2.8 °C | 10 / 23 % | 21 / 17 % | 69 / 60 % |
| 2081–2100, RCP 4.5 | +3.0 / +2.5 °C | 25 / 25 % | 9 / 17 % | 66 / 58 % |
| 2081–2100, RCP 8.5 | +5.5 / +4.5 °C | 0 / 0 % | 0 / 6 % | 100 / 94 % |

- **Through 2050, almost nothing is High** (V1: no cells; V2: under 0.1 %): projected warming stays under 2 °C in
  most cells, so cells that are warm today are Moderate rather than automatically High; the cold Arctic is Low (34 %).
- **2051–2080:** V1 puts about two-thirds of permafrost cells in High under both scenarios (65–69 %). V2 does so only
  under RCP 8.5 (60 %). Under RCP 4.5, V2's median warming (+2.0 °C) sits right on the 2 °C edge, so most cells that
  are near 0 °C or warm today stay Moderate (16 % High).
- **2081–2100:** under RCP 4.5, 58–66 % of cells are High; under RCP 8.5, nearly all (94–100 %), as warming of over
  5 °C lifts even much of the cold Arctic to High.
- **The Arctic holds most of the Low cells** (section 3.2). The Interior, West and South are mostly High from 2051 on
  under V1 (88–100 % of cells), and under V2 only under RCP 8.5 or by 2081–2100 (sections 3.3–3.5).
- **V1 vs V2:** where V2 uses GIPL, 82 % of cells change class in at least one of the six scenario-era combinations,
  almost always with V2 one class lower. The biggest differences: RCP 4.5, 2051–2080 (57 % of cells) and RCP 8.5,
  2051–2080 (26 %). See section 4.

### 3.2 Arctic

319,698 permafrost cells; today's surface temperature: median −4.5 °C (mostly cold, some cool and near 0 °C in the
south). V2 uses GIPL in 99 % of cells.

![Arctic, RCP 4.5](figures/pti_arctic_rcp45.png)

![Arctic, RCP 8.5](figures/pti_arctic_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.6 / +1.3 °C | 77 / 77 % | 23 / 23 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.6 / +1.1 °C | 77 / 77 % | 23 / 23 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.7 / +2.2 °C | 60 / 65 % | 17 / 24 % | 23 / 10 % |
| 2051–2080, RCP 8.5 | +4.0 / +3.3 °C | 23 / 54 % | 48 / 23 % | 29 / 23 % |
| 2081–2100, RCP 4.5 | +3.2 / +2.8 °C | 60 / 59 % | 17 / 18 % | 23 / 23 % |
| 2081–2100, RCP 8.5 | +6.1 / +5.1 °C | 0 / 0 % | 0 / 11 % | 100 / 89 % |

- **Through 2050, mostly Low** (77 %), with Moderate along the southern edge.
- **RCP 4.5:** about a quarter of cells are High in 2051–2100 under V1 (the warmer southern foothills); under V2, 10 %
  in 2051–2080 and 23 % by 2081–2100. The rest stay Low or Moderate.
- **RCP 8.5, 2051–2080:** V1's median warming (+4.0 °C) sits right at the 4 °C edge and puts much of the cold north in
  "Moderate" (cold today, 4–5 °C of warming); V2 (+3.3 °C) keeps it "Low" (cold today, 3–4 °C): 54 % Low against 23 %.
  The straight diagonal line on the V1 map is that edge crossing the coarse air-warming grid; V2 does not have it.
- **RCP 8.5, 2081–2100:** the surface warms by +5.1 to +6.1 °C (median) and ends at about +0.7 to +1.7 °C, as warm
  as or warmer than the Interior's surface today (+0.7 °C). Nearly all cells are High (89–100 %). The "over 5 °C"
  column decides the cold north (49–60 % of cells): without it they would be Moderate (first open question).
- **V1 vs V2:** 69 % of cells change class in at least one combination, nearly all with V2 lower; most under RCP 8.5,
  2051–2080 (41 % of cells) and RCP 4.5, 2051–2080 (18 %). V2 is higher only along the eastern Brooks Range (2 % of
  cells). Fewer than 0.5 % of cells differ by two classes. See section 4.

### 3.3 Interior

347,086 permafrost cells; today's surface temperature: median +0.7 °C (mostly warm surface and near 0 °C). V2 uses
GIPL in 81 % of cells; the other 19 % (GIPL's unusable areas, [GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)) use air warming and
are flagged.

![Interior, RCP 4.5](figures/pti_interior_rcp45.png)

![Interior, RCP 8.5](figures/pti_interior_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.4 / +1.1 °C | 6 / 6 % | 94 / 94 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.3 / +0.9 °C | 6 / 6 % | 94 / 94 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.3 / +1.8 °C | 2 / 4 % | 7 / 71 % | 91 / 25 % |
| 2051–2080, RCP 8.5 | +3.2 / +2.6 °C | 1 / 2 % | 5 / 13 % | 94 / 84 % |
| 2081–2100, RCP 4.5 | +2.7 / +2.3 °C | 1 / 3 % | 5 / 16 % | 94 / 81 % |
| 2081–2100, RCP 8.5 | +5.0 / +4.0 °C | 0 / 0 % | 0 / 3 % | 100 / 97 % |

- **Through 2050, almost all Moderate** (94 %).
- **Most Interior cells are near 0 °C or warm today**, so the 2 °C warming edge alone decides between Moderate and
  High. Under V1, warming passes it in almost every cell from 2051 on (91–100 % High).
- **Under V2, warming sits close to that edge.** Under RCP 4.5 the median is +1.8 °C in 2051–2080 (25 % High) and
  +2.3 °C in 2081–2100 (81 %); under RCP 8.5, +2.6 °C (84 %) and +4.0 °C (97 %).
- **V1 vs V2:** 90 % of the cells where V2 uses GIPL change class in at least one combination, nearly all with V2
  lower; under RCP 4.5, 2051–2080, 85 % of cells. The 19 % of cells without usable GIPL values are identical in both
  versions. See section 4.

### 3.4 West

106,727 permafrost cells; today's surface temperature: median +0.9 °C (nearly all warm surface or near 0 °C). V2
uses GIPL in 96 % of cells.

![West, RCP 4.5](figures/pti_west_rcp45.png)

![West, RCP 8.5](figures/pti_west_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.4 / +1.0 °C | 0 / 0 % | 100 / 100 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.4 / +0.8 °C | 0 / 0 % | 100 / 100 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.5 / +1.7 °C | 0 / 0 % | 0 / 91 % | 100 / 9 % |
| 2051–2080, RCP 8.5 | +3.6 / +2.5 °C | 0 / 0 % | 0 / 4 % | 100 / 96 % |
| 2081–2100, RCP 4.5 | +3.1 / +2.3 °C | 0 / 0 % | 0 / 7 % | 100 / 93 % |
| 2081–2100, RCP 8.5 | +5.6 / +4.1 °C | 0 / 0 % | 0 / 0 % | 100 / 100 % |

- **Through 2050, all Moderate** (100 %).
- **From 2051 on, all High under V1** (100 %).
- **Under V2, RCP 4.5, 2051–2080 is the exception:** warming (+1.7 °C median) stays under 2 °C for most cells, so
  91 % stay Moderate. Otherwise 93–100 % are High.
- **V1 vs V2:** 95 % of cells change class in at least one combination, nearly all in RCP 4.5, 2051–2080 (95 % of
  cells, V2 lower). See section 4.

### 3.5 South

26,125 permafrost cells (the smallest region); today's surface temperature: median +0.4 °C. V2 uses GIPL in 98 % of
cells.

![South, RCP 4.5](figures/pti_south_rcp45.png)

![South, RCP 8.5](figures/pti_south_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.3 / +0.9 °C | 2 / 2 % | 98 / 98 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.2 / +0.6 °C | 2 / 2 % | 98 / 98 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.1 / +1.5 °C | 0 / 2 % | 12 / 94 % | 88 / 4 % |
| 2051–2080, RCP 8.5 | +2.9 / +1.9 °C | 0 / 1 % | 2 / 57 % | 98 / 42 % |
| 2081–2100, RCP 4.5 | +2.6 / +1.9 °C | 0 / 1 % | 2 / 60 % | 97 / 39 % |
| 2081–2100, RCP 8.5 | +4.6 / +3.1 °C | 0 / 0 % | 0 / 2 % | 100 / 98 % |

- **Through 2050, almost all Moderate** (98 %).
- **Under V1, mostly High from 2051 on** (88–100 %).
- **Under V2, GIPL warms least here** (0.6–1.5 °C less than the air), so warming stays near or under 2 °C until late
  in the century: High in 4 % of cells (RCP 4.5, 2051–2080), 39–42 % (RCP 4.5, 2081–2100; RCP 8.5, 2051–2080) and 98 %
  (RCP 8.5, 2081–2100).
- **V1 vs V2:** 97 % of cells change class in at least one combination, and 45 % in three or more, nearly always with
  V2 lower. See section 4.

## 4. Where V1 and V2 differ

V1 and V2 share today's surface temperature and the table; only the projected warming differs (section 2). To see
where that changes the class, each cell's V1 and V2 classes are compared in all six **combinations** of scenario
(RCP 4.5, RCP 8.5) and era (2026–2050, 2051–2080, 2081–2100). Only cells where V2 actually uses GIPL are compared
(724,326 cells, 91 % of permafrost cells). In the rest, V2 uses V1's air warming, so the two are identical by
construction (grey on the maps).

![How often and which way V1 and V2 differ](figures/pti_v1_v2_count.png)

*Left: in how many of the six combinations V1 and V2 give different classes. Right: whether V2's class is higher
than V1's, lower, or higher in some combinations and lower in others.*

![Share of cells where V1 and V2 differ, per area, scenario and era](figures/pti_v1_v2_bars.png)

*Share of each area's cells (where V2 uses GIPL) with a different class in each combination. Red: V2 higher; blue:
V2 lower.*

| Area | Cells where V2 uses GIPL | Same class in all 6 | Differ in 1 / 2 / 3+ combinations | V2 higher only | V2 lower only | Both directions | Most affected scenario and era |
|---|---|---|---|---|---|---|---|
| Statewide | 724,326 | 18 % | 70 / 6 / 6 % | 1 % | 81 % | 0 % | RCP 4.5, 2051–2080: 57 % of cells (V2 lower) |
| Arctic | 317,000 | 31 % | 66 / 3 / 0 % | 2 % | 67 % | 0 % | RCP 8.5, 2051–2080: 41 % (mostly V2 lower) |
| Interior | 279,692 | 10 % | 71 / 9 / 10 % | 0 % | 90 % | 0 % | RCP 4.5, 2051–2080: 85 % (V2 lower) |
| West | 101,947 | 5 % | 87 / 4 / 4 % | 0 % | 95 % | 0 % | RCP 4.5, 2051–2080: 95 % (V2 lower) |
| South | 25,654 | 3 % | 31 / 21 / 45 % | 0 % | 97 % | 0 % | RCP 4.5, 2051–2080: 89 % (V2 lower) |

- **Through 2050, the two agree almost everywhere** (at least 99.9 % of cells in every area): warming is under 2 °C
  in both versions.
- **From 2051 on, V2 is lower almost everywhere**, because GIPL's surface warms less than the air (section 2). V2 is
  higher only along the eastern Brooks Range, where GIPL warms more (2 % of Arctic cells).
- **The differences are always one class** (two classes: 0.1 % of cells at most).
- **They are largest under RCP 4.5 in 2051–2080.** V1's warming sits just above the 2 °C edge there and V2's just
  below it. In the near-0 and warm-surface rows (most of the Interior, West and South) that is the difference between
  High and Moderate, for 85–95 % of those regions' cells. In the Arctic, the 3 °C and 4 °C edges matter too (RCP 8.5,
  2051–2080: 41 % of cells).
- **On the maps**, the two agree in all six combinations across the cold northern Arctic (Low throughout). They
  differ in one combination across most of the state, and in three or more in the southern mountains (Alaska Range,
  Wrangell and Chugach Mountains) and the south-west.
- **For the V1-or-V2 decision:** the choice now changes the overall picture at mid-century. Under RCP 4.5 in
  2051–2080, V1 rates 65 % of permafrost cells High and V2 16 %. It matters most for the Interior, West and South under
  RCP 4.5, and for the Arctic under RCP 8.5.

## 5. Test areas and example data sentences

Generated automatically from V2 (2051–2080, RCP 8.5) and the context layers. The examples are for the 1 km cell at
the centre of each of three 10 × 10 km test areas: Brooks Range (Arctic), Fairbanks and Denali (both Interior).

<img src="figures/pti_test_areas.png" alt="Where the three test areas are" width="55%">

![PTI classes around the three test areas](figures/pti_test_area_maps.png)

*PTI classes (V2, RCP 8.5, 2051–2080) in a 40 × 40 km area around each test area, drawn semi-transparent over
an ArcticDEM hillshade (lit from the south, so north-facing slopes are in shadow); lakes and rivers in blue.
Black square: the 10 × 10 km test area; small outlined cell: the centre cell described by the data sentence
below.*

> **Brooks Range test area:** PTI: ![Moderate](figures/badges/pti_moderate.svg) (2051–2080, RCP 8.5): surface cool
> today (−3.9 °C), projected to warm +3.0 °C. Permafrost extent: continuous (PFR 100 %). Terrain: 78 % shaded slopes,
> which favour permafrost. Land cover: 0 % black spruce / wetland; mostly shrub, tundra or open ground.

> **Fairbanks test area:** PTI: ![High](figures/badges/pti_high.svg) (2051–2080, RCP 8.5): surface above
> 0 °C today (+1.7 °C), projected to warm +3.1 °C. Permafrost extent: sparse (PFR 14 %). Terrain: 70 % sun-facing
> slopes, so permafrost is likely limited to shaded and flat ground. Land cover: 65 % black spruce / wetland
> (insulating organic layer). Note: GIPL unavailable here; air-temperature warming used instead.

> **Denali test area:** PTI: ![Moderate](figures/badges/pti_moderate.svg) (2051–2080, RCP 8.5): surface above 0 °C
> today (+0.2 °C), projected to warm +1.9 °C. Permafrost extent: extensive (PFR 71 %). Terrain: 84 % shaded slopes,
> which favour permafrost. Land cover: 0 % black spruce / wetland; mostly shrub, tundra or open ground.

Draft wording rules:

| Context | Source | Wording |
|---|---|---|
| PTI class | the two-way table (section 1); V2 in these examples | class name, coloured as in the table |
| Today's surface temperature | ESA GST 2014–2023 | cold (below −4 °C), cool (−4 to −2 °C), near 0 °C (−2 to 0 °C), above 0 °C |
| Permafrost extent | ESA PFR 2023 (comes in steps of ~14 %) | sparse (≤ 29 %), patchy (43–57 %), extensive (71–86 %), continuous (100 %) |
| Terrain | share of the cell with sun-facing (TII > 0.1) or shaded (TII < −0.1) slopes | ≥ 40 % sun-facing: "permafrost likely limited to shaded and flat ground"; ≥ 40 % shaded: "favour permafrost"; else "mostly flat or gentle" |
| Land cover | NLCD 2016 evergreen forest + woody and herbaceous wetland | ≥ 50 %: "insulating organic layer"; else "mostly shrub, tundra or open ground" |
| GIPL flag (V2) | GIPL mask ([GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)) | "GIPL unavailable here; air-temperature warming used instead." |

## Open questions

1. **V1 or V2:** where V2 uses GIPL, they give different classes for up to 57 % of cells in one scenario and era
   (RCP 4.5, 2051–2080; 85–95 % in the Interior, West and South), and 82 % of cells differ in at least one of the six
   combinations (section 4). V2 is almost always lower, because GIPL's surface warms about 20 % less than the air.
2. **Table entries.** Most consequential: "cold today, over 5 °C of warming" is High. Under RCP 8.5 the Arctic
   warms by 5–6 °C by 2081–2100, so this one box decides 49–60 % of Arctic cells in that era (they would be Moderate
   without the "over 5 °C" column). With three classes the near-0 and warm-surface rows are identical: keep them as
   two rows, or merge them?
3. **Band edges:** today −4 / −2 / 0 °C; warming 2 / 3 / 4 / 5 °C. Much of the projected warming sits close to an
   edge that changes the class: the 2 °C edge for the Interior, West and South at mid-century (V2 under RCP 4.5 sits
   just below it, V1 just above), and the 4 °C edge for the Arctic under RCP 8.5 in 2051–2080. Moving an edge by half
   a degree would change many classes there.
4. **Data sentence wording and thresholds** (40 % terrain, 50 % land cover) are drafts.

## Notes

- ⚠️ The table is a judgement: there is no data to calibrate its entries, and band edges create steps (a cell at −2.1 °C
  and one at −1.9 °C can land in different rows).
- ⚠️ Surface temperature is not actual permafrost temperature: snow, vegetation and soil decide how surface warming reaches
  the permafrost below.
- 5-model average only; single climate models and the full uncertainty range are not shown.
- V1, and V2 where GIPL is unavailable, use air warming as a stand-in for ground-surface warming.
- V2 relies on GIPL's projected *changes*; GIPL's own temperature levels are not used
  ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)). Why GIPL's warming lags the air's is only partly explained
  (section 2).
- GIPL's files are labelled 20 years late; V2 reads them on the climate years they carry. This shift is inferred from
  the data, not documented ([GIPL_ISSUE_3.md](GIPL_ISSUE_3.md)).

<sub>Methods: 1 km GIPL grid; permafrost cells = ESA CCI Permafrost v5 PFR 2023 > 0; today = ESA ground surface
temperature 2014–2023 (sampled at cell centres); air temperature = SNAP 2 km 5-model average (parent cell); V1
warming = model air temperature, era minus 2014–2023; V2 warming = GIPL surface temperature, era minus 2014–2023, on
climate years (GIPL files labelled 20 years later, [GIPL_ISSUE_3.md](GIPL_ISSUE_3.md); delta change method), on cells
where GIPL is usable ([GIPL_ISSUE_1.md](GIPL_ISSUE_1.md)). Seasonal air warming (section 2): December–February and
June–August means, era minus 2014–2023, on cells where GIPL is usable (`scripts/02_tests/t4b_seasonal_warming.py`).
Ground and air warming rates: `scripts/02_tests/t6_gipl_levels.py` (trends). Table breaks: today −4 / −2 / 0 °C;
warming 2 / 3 / 4 / 5 °C. V1 vs V2 (section 4): classes compared cell by cell in each of the six scenario × era
combinations, on permafrost cells where V2 uses GIPL. Data sentences: the 1 km cell at the centre of each test area;
class badges in `docs/figures/badges/`. Terrain from the 32 m terrain insolation index; land cover from NLCD 2016
(30 m). Scripts: `scripts/02_tests/t4_index_variants.py` (`TABLE`, `TODAY_EDGES`, `WARM_EDGES`; data sentences),
`scripts/03_report/pti_results_figures.py` (section 3), `scripts/03_report/pti_extra_figures.py` (section 4 and the
test-area map), `scripts/03_report/test_area_maps.py` (test-area class maps); per-cell results and summary tables
(`pti_area_summary.csv`, `v1_v2_differences.csv`, `sentences.csv`) in `<data>/results/t4/`. Alternatives that were
tested and set aside are archived in [PTI_EXPERIMENTS.md](PTI_EXPERIMENTS.md).</sub>
