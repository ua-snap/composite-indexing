# Wildfire: decisions

Newest first. One row per decision: what was decided, why, and who decided (team, or a person). Open questions live
in the README.

| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-11-10 | Fire weather variants: B season mean, C peak week (7-day rolling mean), D summer days with High or worse fire danger (FWI ≥ 18), as the SNAP API's operations, computed from the local release; outside the boreal domain = fixed Low | Compare the API's summaries; no fire weather data outside the boreal region | Joshdpaul |
| 2026-11-10 | Retire `flam-change`; Variant B = Fire Weather Index at mid-century (`fwi-future`: mean April–October FWI, 2040–2069, 4 CMIP6 models, SSP5-8.5), from the local copy of SNAP's release | Change in flammability is not meaningful: a place that burns often both before and after shows 0 change and would be Low, though it is highly flammable | Joshdpaul |
| 2026-10-27 | Change = absolute change in flammability (not %) | A third of burnable land starts at 0, so % is undefined there | Joshdpaul |
| 2026-10-27 | Baseline = Rasdaman 1980–2008 historical run, not SNAP's local yearly GeoTIFFs | The local files are a different product (0/1 burned; none of the 3 fire-management versions matches) | Joshdpaul |
| 2026-10-27 | Maps show raw 1 km pixels; the point value uses the SNAP API watershed (HUC-12) average | SNAP advises against reading single ALFRESCO pixels | Joshdpaul |
| 2026-10-27 | Dataset = ALFRESCO relative flammability, 2040–2069, 5-model average, RCP 4.5 | Workbench: one dataset per index, mid-century, middle emissions | Joshdpaul |
