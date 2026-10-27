# Combining playbook

**Short answer:** the app already has five combining rules; what's missing is evidence for choosing one. Next we
measure how each rule behaves (how much land ends up High, how sensitive it is to one index), write down candidate
presets the team can react to, and pick a handful of real places to test against. Most of this is analysis of the
existing variants, so it can run alongside the three index workstreams.

**Key terms**
- **Rule:** how three classes become one (worst of three, weighted average of points, product of points, count the
  Highs, or a hand-set 27-cell table).
- **Preset:** a named set of variants + class boundaries + rule (`presets/*.json`), opened with `#preset-<id>`.

## 1. Decide first: what is the Environmental Hazard for?
- **Screening** ("flag anything with one serious hazard": worst of three) or **ranking** ("which places carry the most
  combined hazard": average, product or count)?
- Who reads it: planners choosing sites, engineers, communities? That sets how much High is too much.

**From the Arctic-EDS Candidate Data Catalog:** the catalog has six hazard topics: Climate, Permafrost, Wildfire,
Hydrology, Sea Ice and Sea Level. Each lists the assets it threatens (buildings, roads, airstrips, water/sewer,
personnel, equipment, land/air/sea travel). Two consequences for this workstream:
- The rule should work for more than three indices: climate extremes, flooding, sea ice and sea level are natural
  later additions.
- The same hazard can matter differently by asset (smoke matters to personnel and air travel, thaw to buildings and
  roads), so a preset per asset type may be more useful than one universal rule.

## 2. Where we start
Rule "worst of three", missing index = Low, equal weights. Presets `future` and `change`. Worst of three puts 52–72 %
of land in High, mostly because permafrost (future) or erosion is High in so much of the state.

## 3. Work backlog
| Item | What | Data | Priority |
|---|---|---|---|
| Rule profiles | for each rule: land share per class, and how often each index decides the hazard | existing variants | 1 |
| Sensitivity | how the hazard map moves when one index swaps variant or its boundaries move ±10 % | existing variants | 1 |
| Test places | 10–20 places the team knows (communities, sites, infrastructure) with expected answers | team list | 1 |
| Candidate presets | e.g. `screening` (worst of three), `balanced` (average, cuts 1.5/2.5), `two-of-three` (count Highs ≥ 2) | presets | 1 |
| Regional view | hazard class shares by region (Arctic / Interior / West / South) | `features/regions_1km.tif` | 2 |
| Area hazard | hazard summarized over a community or route buffer, not one pixel | app + boundaries | 3 |

## 4. How we'll compare rules
- Share of land in each class (too much High = no information).
- Agreement with the team's test places.
- Explainability: can the hazard at a place be traced to the index that caused it in one sentence?

## 5. Decisions for the team
1. Screening or ranking (section 1).
2. Equal weights, or does one hazard count more?
3. Missing index: count as Low, or leave the hazard blank?
4. Mixing change and level variants in one preset: fine for exploration; for the final index?
5. One hazard for everything, or presets per asset type (infrastructure, personnel, travel)?
6. Which catalog topics become indices next (climate extremes, flooding, sea ice, sea level)? The app currently
   assumes three indices; a fourth means generalizing the rule card and the 27-cell table.

## 6. First session
1. Rule profiles and sensitivity for the `future` and `change` presets (a small script; results into this README).
2. Add the three candidate presets.
3. Ask the team for the test-place list.
