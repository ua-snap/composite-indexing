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
- **Through 2050, almost no cell is High** (warming mostly stays under 2 °C). By 2051–2080, about two-thirds of
  permafrost cells are High (65–69 %); by 2081–2100 under RCP 8.5, nearly all (98–100 %).
- **Two versions, differing only in where the projected warming comes from:** V1 uses air temperature (no GIPL); V2
  uses GIPL, with air temperature where GIPL has no usable values (about 1 in 5 Interior cells, flagged). Where V2
  uses GIPL, the two give the same class for 80–100 % of cells, depending on scenario and era; the differences are
  mostly in the Arctic, and almost always by one class (section 4).
- **Permafrost extent, terrain and land cover stay out of the number** and go in the data sentence.
- **Decisions needed:** the table's entries and band edges (especially the "over 5 °C" column, which decides the
  Arctic under RCP 8.5 by 2081–2100), and whether to adopt V1 or V2.

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
- **Projected warming:** how much the ground surface warms from today to an era (2026–2050, 2051–2080, 2081–2100),
  under a greenhouse-gas scenario (RCP 4.5: moderate; RCP 8.5: high), using the 5-climate-model average.
- **Delta change method:** future = today's observed level + the change a model projects; the model contributes only
  its change ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)).
- **V1:** projected warming = air-temperature warming (SNAP 2 km downscaled climate). No GIPL.
- **V2:** projected warming = GIPL ground-surface warming (delta change method). Where GIPL has no usable values
  ([GIPL_ISSUE.md](GIPL_ISSUE.md)), V1's air warming is used and the cell is flagged.
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
- The **over 5 °C** column is the 4–5 °C column moved up one class (High stays High), so it changes only the cold row.
  It matters for the Arctic under RCP 8.5 by 2081–2100: its surface warms by 5.5–6 °C (median) and ends above 0 °C,
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
  ([GIPL_ISSUE.md](GIPL_ISSUE.md)), and its temperature levels do not match today's observation-based values, so only
  its *change* is used ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)). **V2** uses GIPL's warming where it is usable
  and air warming elsewhere (flagged).

Neither can be checked against future observations, so both are shown; which one to adopt is an open question.

| | Projected warming from | Uses GIPL | Cells with a class: all of Alaska | Cells with a class: Interior |
|---|---|---|---|---|
| **V1** | air temperature (SNAP 2 km, 5-model average) | no | 100 % | 100 % |
| **V2** | GIPL ground surface (delta change method); air temperature where GIPL has no usable values, flagged | yes | 100 % (GIPL in 91 %) | 100 % (GIPL in 81 %) |

Both use the same today's surface temperature and the same table.

### Why GIPL's ground surface warms differently from the air

<img src="figures/t4_gipl_minus_air.png" alt="Where GIPL's surface warming differs from air warming" width="55%">

*V2 − V1 projected warming, 2051–2080, RCP 8.5. Blue: GIPL's ground surface warms less than the air; red: more.*

- **The air warms much more in winter than in summer**: winter (December–February) warming is about twice summer
  (June–August) warming in the Arctic, Interior and West, and 1.2–1.5 times in the South; the gap is largest in the
  Arctic.
- **Snow insulates the ground in winter.** Under a snowpack, winter air warming reaches the ground surface only
  partly, so where warming is concentrated in winter, GIPL's surface warms less than the air. The data agree: the
  larger a cell's winter-over-summer warming, the more GIPL lags the air (statewide Spearman ρ = −0.70 under RCP 8.5,
  2051–2080), and the lag is largest in the Arctic.
- **That is not the whole story.** Under RCP 4.5, GIPL warms slightly *more* than the air overall, and in the West the
  relationship reverses. Snow changes in other ways too (for example, a shorter snow season exposes the ground to
  warmer air in spring), and GIPL's snow and soil inputs are not documented, so these effects cannot be separated.

| 2051–2080, RCP 4.5 / RCP 8.5 | Winter air warming | Summer air warming | V2 − V1 (annual ground surface) |
|---|---|---|---|
| Statewide | +3.6 / +4.4 °C | +1.7 / +2.6 °C | +0.3 / −0.3 °C |
| Arctic | +4.1 / +5.3 °C | +1.7 / +2.8 °C | +0.1 / −0.7 °C |
| Interior | +3.2 / +3.9 °C | +1.6 / +2.5 °C | +0.4 / −0.1 °C |
| West | +3.7 / +4.6 °C | +1.7 / +2.5 °C | +0.2 / −0.3 °C |
| South | +2.7 / +3.1 °C | +1.8 / +2.6 °C | +0.2 / −0.1 °C |

Because a difference of half a degree can move a cell across a warming band, V1 and V2 do not always give the same
class. Where V2 uses GIPL, they agree for nearly all cells through 2050, and for 80–98 % of cells in the later
eras; section 4 maps where they differ. Each area in section 3 lists its own median warming for V1 and V2.

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
| 2026–2050, RCP 4.5 | +1.5 / +1.4 °C | 34 / 34 % | 66 / 66 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.4 / +1.6 °C | 34 / 34 % | 66 / 66 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.5 / +2.7 °C | 25 / 25 % | 10 / 11 % | 65 / 65 % |
| 2051–2080, RCP 8.5 | +3.5 / +3.2 °C | 10 / 24 % | 21 / 10 % | 69 / 66 % |
| 2081–2100, RCP 4.5 | +3.0 / +3.5 °C | 25 / 18 % | 9 / 14 % | 66 / 67 % |
| 2081–2100, RCP 8.5 | +5.5 / +5.0 °C | 0 / 0 % | 0 / 2 % | 100 / 98 % |

- **Through 2050, almost nothing is High** (V1: no cells; V2: under 0.5 %): projected warming stays mostly under
  2 °C, so cells that are warm today are Moderate rather than automatically High; the cold Arctic is Low (34 %).
- **By 2051–2080, about two-thirds of permafrost cells are High** (65–69 %), in both scenarios and both versions.
  Under RCP 4.5 that share hardly grows by 2081–2100 (66–67 %); under RCP 8.5 it reaches nearly all cells
  (98–100 %), as warming of over 5 °C lifts even the cold Arctic to High.
- **The Arctic holds almost all of the Low and Moderate cells** (section 3.2); the Interior, West and South are mostly
  High from 2051 on (82–100 % of cells).
- **V1 vs V2:** where V2 uses GIPL, 26 % of cells change class in at least one of the six scenario-era combinations,
  almost always by one class. The biggest differences: RCP 8.5, 2051–2080 (20 % of cells, mostly V2 lower) and RCP
  4.5, 2081–2100 (8 %, V2 higher), both mostly in the Arctic. See section 4.

### 3.2 Arctic

319,698 permafrost cells; today's surface temperature: median −4.5 °C (mostly cold, some cool and near 0 °C in the
south). V2 uses GIPL in 99 % of cells.

![Arctic, RCP 4.5](figures/pti_arctic_rcp45.png)

![Arctic, RCP 8.5](figures/pti_arctic_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.6 / +1.4 °C | 77 / 77 % | 23 / 23 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.6 / +1.6 °C | 77 / 77 % | 23 / 23 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.7 / +2.9 °C | 60 / 60 % | 17 / 17 % | 23 / 23 % |
| 2051–2080, RCP 8.5 | +4.0 / +3.4 °C | 23 / 57 % | 48 / 20 % | 29 / 23 % |
| 2081–2100, RCP 4.5 | +3.2 / +3.7 °C | 60 / 44 % | 17 / 31 % | 23 / 25 % |
| 2081–2100, RCP 8.5 | +6.1 / +5.5 °C | 0 / 0 % | 0 / 3 % | 100 / 97 % |

- **Through 2050, mostly Low** (77 %), with Moderate along the southern edge.
- **RCP 4.5:** about a quarter of cells are High in 2051–2100 (the warmer southern foothills); the rest stay Low or
  Moderate.
- **RCP 8.5, 2051–2080:** median warming sits right at the 4 °C edge. V1 (+4.0 °C) puts much of the cold north in
  "Moderate" (cold today, 4–5 °C of warming), V2 (+3.4 °C) in "Low" (cold today, 3–4 °C). The straight diagonal line
  on the V1 map is that edge crossing the coarse air-warming grid; V2 does not have it.
- **RCP 8.5, 2081–2100:** the surface warms by +5.5 to +6.1 °C (median) and ends at about +1.0 to +1.7 °C, warmer
  than the Interior's surface today (+0.7 °C). Nearly all cells are High (97–100 %). The "over 5 °C" column decides
  the cold north (58–60 % of cells): without it they would be Moderate (first open question).
- **V1 vs V2:** 53 % of cells change class in at least one combination. Under RCP 8.5, 2051–2080, V2 is mostly lower
  (43 % of cells; see above); under RCP 4.5, 2081–2100, it is higher (18 %). Fewer than 0.5 % of cells differ by two
  classes. See section 4.

### 3.3 Interior

347,086 permafrost cells; today's surface temperature: median +0.7 °C (mostly warm surface and near 0 °C). V2 uses
GIPL in 81 % of cells; the other 19 % (GIPL's unusable areas, [GIPL_ISSUE.md](GIPL_ISSUE.md)) use air warming and
are flagged.

![Interior, RCP 4.5](figures/pti_interior_rcp45.png)

![Interior, RCP 8.5](figures/pti_interior_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.4 / +1.5 °C | 6 / 6 % | 94 / 94 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.3 / +1.6 °C | 6 / 6 % | 94 / 94 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.3 / +2.6 °C | 2 / 1 % | 7 / 7 % | 91 / 92 % |
| 2051–2080, RCP 8.5 | +3.2 / +3.1 °C | 1 / 1 % | 5 / 5 % | 94 / 94 % |
| 2081–2100, RCP 4.5 | +2.7 / +3.3 °C | 1 / 1 % | 5 / 5 % | 94 / 94 % |
| 2081–2100, RCP 8.5 | +5.0 / +4.7 °C | 0 / 0 % | 0 / 1 % | 100 / 98 % |

- **Through 2050, almost all Moderate** (94 %).
- **From 2051 on, over 90 % High** (91–100 %) in both scenarios and both versions. Most Interior cells are near 0 °C
  or warm today, and in those rows any warming above 2 °C is High, so the 3 °C edge does not matter here.
- **V1 vs V2:** 5 % of the cells where V2 uses GIPL change class in at least one combination (at most 2 % in any one).
  The 19 % of cells without usable GIPL values are identical in both versions. See section 4.

### 3.4 West

106,727 permafrost cells; today's surface temperature: median +0.9 °C (nearly all warm surface or near 0 °C). V2
uses GIPL in 96 % of cells.

![West, RCP 4.5](figures/pti_west_rcp45.png)

![West, RCP 8.5](figures/pti_west_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.4 / +1.4 °C | 0 / 0 % | 100 / 100 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.4 / +1.6 °C | 0 / 0 % | 100 / 98 % | 0 / 2 % |
| 2051–2080, RCP 4.5 | +2.5 / +2.6 °C | 0 / 0 % | 0 / 1 % | 100 / 99 % |
| 2051–2080, RCP 8.5 | +3.6 / +3.2 °C | 0 / 0 % | 0 / 0 % | 100 / 100 % |
| 2081–2100, RCP 4.5 | +3.1 / +3.3 °C | 0 / 0 % | 0 / 0 % | 100 / 100 % |
| 2081–2100, RCP 8.5 | +5.6 / +4.8 °C | 0 / 0 % | 0 / 0 % | 100 / 100 % |

- **Through 2050, almost all Moderate** (98–100 %).
- **From 2051 on, essentially all High** (99–100 %) in both scenarios and both versions.
- **V1 vs V2:** 3 % of cells change class in at least one combination (V2 higher under RCP 8.5, 2026–2050: 2 % of
  cells). See section 4.

### 3.5 South

26,125 permafrost cells (the smallest region); today's surface temperature: median +0.4 °C. V2 uses GIPL in 98 % of
cells.

![South, RCP 4.5](figures/pti_south_rcp45.png)

![South, RCP 8.5](figures/pti_south_rcp85.png)

| Era, scenario | Projected warming, median (V1 / V2) | Low | Moderate | High |
|---|---|---|---|---|
| 2026–2050, RCP 4.5 | +1.3 / +1.3 °C | 2 / 2 % | 98 / 98 % | 0 / 0 % |
| 2026–2050, RCP 8.5 | +1.2 / +1.5 °C | 2 / 2 % | 98 / 98 % | 0 / 0 % |
| 2051–2080, RCP 4.5 | +2.1 / +2.4 °C | 0 / 0 % | 12 / 18 % | 88 / 82 % |
| 2051–2080, RCP 8.5 | +2.9 / +2.8 °C | 0 / 0 % | 2 / 3 % | 98 / 97 % |
| 2081–2100, RCP 4.5 | +2.6 / +3.0 °C | 0 / 0 % | 2 / 2 % | 97 / 98 % |
| 2081–2100, RCP 8.5 | +4.6 / +4.0 °C | 0 / 0 % | 0 / 0 % | 100 / 100 % |

- **Through 2050, almost all Moderate** (98 %).
- **2051–2080:** mostly High in both scenarios. Under RCP 4.5 the median warming (+2.1 to +2.4 °C) sits just above
  the 2 °C edge, so 12–18 % of cells are still Moderate; under RCP 8.5, 97–98 % are High.
- **2081–2100:** nearly all High (97–100 %).
- **V1 vs V2:** 15 % of cells change class in at least one combination, nearly all under RCP 4.5, 2051–2080 (13 % of
  cells, mostly V2 lower). See section 4.

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
| Statewide | 724,326 | 74 % | 20 / 6 / 0 % | 4 % | 17 % | 5 % | RCP 8.5, 2051–2080: 20 % of cells (mostly V2 lower) |
| Arctic | 317,000 | 47 % | 39 / 14 / 0 % | 7 % | 34 % | 12 % | RCP 8.5, 2051–2080: 46 % (mostly V2 lower) |
| Interior | 279,692 | 95 % | 4 / 1 / 0 % | 2 % | 3 % | 0 % | RCP 4.5, 2051–2080: 2 % (mostly V2 higher) |
| West | 101,947 | 97 % | 3 / 0 / 0 % | 2 % | 1 % | 0 % | RCP 8.5, 2026–2050: 2 % (V2 higher) |
| South | 25,654 | 85 % | 15 / 0 / 0 % | 4 % | 11 % | 0 % | RCP 4.5, 2051–2080: 13 % (mostly V2 lower) |

- **Through 2050, the two agree almost everywhere** (at least 98 % of cells in every area): warming is mostly under
  2 °C in both versions.
- **Most cells that differ do so in only one or two of the six combinations**, and almost always by one class (two
  classes: 0.1 % of cells statewide, 0.2 % in the Arctic).
- **The differences are mostly in the Arctic.** Most Interior, West and South cells are near 0 °C or warm today, and
  in those two rows every warming band above 2 °C is High, so only the 2 °C edge can change their class. Arctic cells
  sit in the cold and cool rows, where the 3 and 4 °C edges also change the class.
- **The direction follows section 2.** Under RCP 8.5, GIPL's surface warms less than the air (partly because snow
  shields the ground from winter warming), so V2 is a class lower: most of all in the Arctic in 2051–2080, near the
  4 °C edge. Under RCP 4.5, GIPL's surface warms slightly more than the air, so V2 is a class higher where warming
  sits just below an edge: most of all in the Arctic in 2081–2100 (18 % of Arctic cells).
- **On the maps**, V2 is mostly lower across the northern Arctic and the western Brooks Range, and higher along the
  eastern Brooks Range; in the north-west Arctic it is higher in some combinations and lower in others. Elsewhere the two agree
  almost everywhere, apart from scattered cells along the south coast.
- **For the V1-or-V2 decision:** the choice moves classes by one step, in one or two combinations per cell; it does
  not change the overall picture in section 3. It matters mainly for the Arctic (RCP 8.5, 2051–2080: 46 % of Arctic
  cells) and, less, for the South under RCP 4.5 in 2051–2080 (13 %).

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
> today (−3.9 °C), projected to warm +3.4 °C. Permafrost extent: continuous (PFR 100 %). Terrain: 78 % shaded slopes,
> which favour permafrost. Land cover: 0 % black spruce / wetland; mostly shrub, tundra or open ground.

> **Fairbanks test area:** PTI: ![High](figures/badges/pti_high.svg) (2051–2080, RCP 8.5): surface above
> 0 °C today (+1.7 °C), projected to warm +3.1 °C. Permafrost extent: sparse (PFR 14 %). Terrain: 70 % sun-facing
> slopes, so permafrost is likely limited to shaded and flat ground. Land cover: 65 % black spruce / wetland
> (insulating organic layer). Note: GIPL unavailable here; air-temperature warming used instead.

> **Denali test area:** PTI: ![High](figures/badges/pti_high.svg) (2051–2080, RCP 8.5): surface above 0 °C today
> (+0.2 °C), projected to warm +2.8 °C. Permafrost extent: extensive (PFR 71 %). Terrain: 84 % shaded slopes, which
> favour permafrost. Land cover: 0 % black spruce / wetland; mostly shrub, tundra or open ground.

Draft wording rules:

| Context | Source | Wording |
|---|---|---|
| PTI class | the two-way table (section 1); V2 in these examples | class name, coloured as in the table |
| Today's surface temperature | ESA GST 2014–2023 | cold (below −4 °C), cool (−4 to −2 °C), near 0 °C (−2 to 0 °C), above 0 °C |
| Permafrost extent | ESA PFR 2023 (comes in steps of ~14 %) | sparse (≤ 29 %), patchy (43–57 %), extensive (71–86 %), continuous (100 %) |
| Terrain | share of the cell with sun-facing (TII > 0.1) or shaded (TII < −0.1) slopes | ≥ 40 % sun-facing: "permafrost likely limited to shaded and flat ground"; ≥ 40 % shaded: "favour permafrost"; else "mostly flat or gentle" |
| Land cover | NLCD 2016 evergreen forest + woody and herbaceous wetland | ≥ 50 %: "insulating organic layer"; else "mostly shrub, tundra or open ground" |
| GIPL flag (V2) | GIPL mask ([GIPL_ISSUE.md](GIPL_ISSUE.md)) | "GIPL unavailable here; air-temperature warming used instead." |

## Open questions

1. **Table entries.** Most consequential: "cold today, over 5 °C of warming" is High. Under RCP 8.5 the Arctic
   warms by 5.5–6 °C by 2081–2100, so this one box decides 58–60 % of Arctic cells in that era (they would be
   Moderate without the "over 5 °C" column). With three classes the near-0 and warm-surface rows are identical: keep
   them as two rows, or merge them?
2. **Band edges:** today −4 / −2 / 0 °C; warming 2 / 3 / 4 / 5 °C. Some areas' warming sits close to an edge that
   changes their class (the Arctic near 4 °C under RCP 8.5 in 2051–2080; the South near 2 °C under RCP 4.5 in
   2051–2080), so moving an edge by half a degree would change many classes there.
3. **V1 or V2:** where V2 uses GIPL, they give different classes for up to 20 % of cells in one scenario and era
   (46 % in the Arctic), and 26 % of cells differ in at least one of the six combinations (section 4).
4. **Data sentence wording and thresholds** (40 % terrain, 50 % land cover) are drafts.

## Notes

- ⚠️ The table is a judgement: there is no data to calibrate its entries, and band edges create steps (a cell at −2.1 °C
  and one at −1.9 °C can land in different rows).
- ⚠️ Surface temperature is not actual permafrost temperature: snow, vegetation and soil decide how surface warming reaches
  the permafrost below.
- 5-model average only; single climate models and the full uncertainty range are not shown.
- V1, and V2 where GIPL is unavailable, use air warming as a stand-in for ground-surface warming.
- V2 relies on GIPL's projected *changes*; GIPL's own temperature levels are not used
  ([ESA_GIPL_SPLICING.md](ESA_GIPL_SPLICING.md)). Why GIPL's warming differs from air warming is only partly
  explained (section 2).

<sub>Methods: 1 km GIPL grid; permafrost cells = ESA CCI Permafrost v5 PFR 2023 > 0; today = ESA ground surface
temperature 2014–2023 (sampled at cell centres); air temperature = SNAP 2 km 5-model average (parent cell); V2 warming
= model air warming 2014–2023 → 2026–2035 ("bridge") + GIPL surface change from 2026–2035 (delta change method), on
cells where GIPL is usable ([GIPL_ISSUE.md](GIPL_ISSUE.md)). Seasonal air warming (section 2): December–February and
June–August means, era minus 2014–2023, on cells where GIPL is usable (`scripts/02_tests/t4b_seasonal_warming.py`).
Table breaks: today −4 / −2 / 0 °C; warming 2 / 3 / 4 / 5 °C. V1 vs V2 (section 4): classes compared cell by cell
in each of the six scenario × era combinations, on permafrost cells where V2 uses GIPL. Data sentences: the 1 km cell
at the centre of each test area; class badges in `docs/figures/badges/`. Terrain from the 32 m terrain insolation
index; land cover from NLCD 2016 (30 m). Scripts: `scripts/02_tests/t4_index_variants.py` (`TABLE`, `TODAY_EDGES`,
`WARM_EDGES`; data sentences), `scripts/03_report/pti_results_figures.py` (section 3),
`scripts/03_report/pti_extra_figures.py` (section 4 and the test-area map), `scripts/03_report/test_area_maps.py` (test-area class maps); per-cell results and summary tables
(`pti_area_summary.csv`, `v1_v2_differences.csv`, `sentences.csv`) in `<data>/results/t4/`. Alternatives that were
tested and set aside are archived in [PTI_EXPERIMENTS.md](PTI_EXPERIMENTS.md).</sub>
