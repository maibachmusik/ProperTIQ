# Tasks 006 — Site & terrain rules

- [x] **T1 — new blocks.** `WithinDistance`, `CountRange`, `Facing` (filters);
  `NearbyCount` (criterion). Exported from `propertiq`. → FR-S1..S4.
- [x] **T2 — registry category.** Add `category` to `BlockSpec`; backfill all
  blocks; new blocks in "Site & terrain" / "Proximity & access"; `categories()`
  helper. → FR-S5.
- [x] **T3 — tests.** `test_site_terrain.py` (hand-checked survivors/scores incl.
  Facing wraparound); registry category + drift; count-partition. → SC-S1, SC-S2.
- [x] **T4 — app grouping.** Block pickers grouped by category
  ("Category · Label"). → FR-S5.
- [x] **T5 — app enrichment.** `app/_enrich.py`: fast 3DEP terrain
  (`slope_deg`/`aspect_deg`, centroid sampling) on load; OSM structures + site
  layers (buildings/water/power/roads) on demand. → FR-S6, SC-S3.
- [x] **T6 — docs + gate.** Blocks page groups by category; ruff + mypy + pytest
  green; live verify (Front Range load shows terrain + Site & terrain picker).

## Deferred (documented in spec)
Raster canopy/NDVI vegetation density and SSURGO soils; water/mineral rights stay
bring-your-own (no clean open parcel attribute).
