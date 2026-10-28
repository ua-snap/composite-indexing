# Combining the indices

**Question:** how should Wildfire, Erosion and Permafrost classes combine into one Environmental Hazard class?

## Decisions
The team picks each index's variant and boundaries on the index pages and the rule on the Environmental Hazard page
of the app, and saves them there. [decisions.json](decisions.json) is the repo copy: Claude refreshes it from the app,
and the app uses it for anything the team hasn't decided yet (today: Variant A of each index, worst of three).

## Rules in the app
Worst of the three · weighted average of points · product of points · count the Highs · custom 27-cell table. The rule
and its settings are saved with the team decision.

## Open questions
- Should one High always make the hazard High ("worst of three" puts 52–72 % of land in High)?
- Weights per index, and whether a missing index counts as Low or blanks the hazard.
