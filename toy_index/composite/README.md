# Combining the indices

**Question:** how should Wildfire, Erosion and Permafrost classes combine into one Environmental Hazard class?

## Presets
A preset names a set of variants and, optionally, their class boundaries and the combining rule. It shows up in the
app's **Preset** picker and opens from a link ending in `#preset-<id>`.

| id | Variants | Rule |
|---|---|---|
| `future` | flam-future · storm-24h-100yr-future · temp-1m-future | app default (worst of three) |
| `change` | flam-change · storm-24h-100yr-change · thaw-progress | app default (worst of three) |

To save a setup the team agreed on: **Copy settings** in the app, take the JSON at the end, save it here as
`presets/<id>.json` (fill in `name` and `description`), and rebuild the app.

## Rules in the app
Worst of the three · weighted average of points · product of points · count the Highs · custom 27-cell table. Each
rule's settings can be stored in a preset.

## Open questions
- Should one High always make the hazard High ("worst of three" puts 52–72 % of land in High)?
- Weights per index, and whether a missing index counts as Low or blanks the hazard.
