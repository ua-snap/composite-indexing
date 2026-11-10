# Permafrost: decisions

Newest first. One row per decision: what was decided, why, and who decided (team, or a person). Open questions live
in the README.

| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-11-09 | Retire `surface-warming` (warming only); `esa-plus-warming` becomes Variant C | Surface warming is largest in the Arctic (Arctic amplification), which doesn't mean its permafrost is thawing; the Interior and Seward Peninsula are known to have the highest thaw hazard | Joshdpaul |
| 2026-11-09 | Gate every permafrost variant (A–D) with ESA CCI permafrost presence (PFR 2023 > 0, as PTI); outside the permafrost zone the class is always Low | No permafrost, nothing to thaw | Joshdpaul |
| 2026-11-09 | Measure warming over time, not a 0 °C threshold | GIPL investigation (docs/GIPL_ISSUE_2.md): GIPL's 0 °C line is fragile as an absolute frozen/thawed split | Joshdpaul |
| 2026-10-27 | Change = progress to thaw (crosses 0 °C = 100 %); ground not frozen at the start counts as Low | No separate permafrost-extent dataset in the workbench: GIPL's own baseline is the filter | Joshdpaul |
| 2026-10-27 | Mask GIPL stuck cells and a 2 km border (D17) | Stuck cells don't respond to climate (docs/GIPL_ISSUE_1.md) | Joshdpaul |
| 2026-10-27 | Dataset = GIPL 2.0 ground temperature at 1 m, 2040–2069, 5-model average, RCP 4.5 | Workbench: one dataset per index | Joshdpaul |
