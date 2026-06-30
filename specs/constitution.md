# ProperTIQ — Constitution

Non-negotiables. Every spec, plan, and PR is checked against these. Changing a
principle here is a deliberate amendment, not a drive-by edit.

1. **Explainable scoring — no black box.** Every score decomposes into a
   per-criterion `score_breakdown` whose contributions sum to the score. If a
   number can't be explained, it doesn't ship.
2. **Bring-your-own-data.** ProperTIQ owns the *method*, never the data. The
   library never bundles, hosts, or silently fetches parcel/layer data. Loaders
   (v0.3) are thin conveniences over open sources, always optional.
3. **One metric CRS for all area/distance, always validated.** Inputs are
   reprojected to a measurement CRS (default EPSG:5070) before any area or
   distance math; geometry is validated; mismatched-CRS inputs are warned and
   reprojected — **never silently joined**.
4. **Filters and criteria are independent, testable units.** Each is a small,
   self-contained class with its own test. Adding one is a small PR.
5. **Results always export to open formats** (GeoJSON, GeoParquet) carrying the
   stated CRS and scores.
6. **Small, composable surface over a thin geopandas core.** No framework, no
   service, no GUI. Typed, linted, tested.

Reproducibility is implied throughout: same inputs → same scores, deterministically.
