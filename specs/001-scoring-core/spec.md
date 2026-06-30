# Spec 001 — Scoring Core (v0.1)

**Status:** ready to implement · **Milestone:** v0.1 · **Covers:** FR-1…FR-7
**Constitution:** principles 1, 3, 4, 5, 6 apply.

## Summary
The scoring engine: compose a `Strategy` from hard filters + weighted criteria,
run it over a parcel `GeoDataFrame`, and get back a `Result` with each surviving
parcel scored `0–100`, ranked, and carrying a transparent per-criterion
`score_breakdown`. This spec also covers CRS normalization (folds in
`spec: crs-handling`) and open-format export, since v0.1 needs them end-to-end.

## Goals
- Deterministic, explainable weighted scoring with a breakdown that **sums to the score**.
- Correct area/distance math in a single metric CRS.
- BYO data: works on any user-supplied `GeoDataFrame`s; nothing fetched or bundled.

## Non-goals (v0.1)
- YAML loader (`spec 003`, v0.2). `.to_map()` / rich `.explain()` rendering (v0.2).
- `loaders/` for open data (v0.3). Raster criteria; drive-time. Per-AOI UTM auto-pick.

## User scenarios
- **P1 (MVP):** An analyst has a parcels `GeoDataFrame` and a few layers
  (highways, competitor POIs). They write a `Strategy`, call `.run(parcels)`, and
  get a ranked frame whose top candidates and scores reproduce a hand-checked overlay.
- **P2:** They call `result.to_file("candidates.geojson")` and the file holds all
  survivors with `score`, `rank`, and the breakdown.

## The scoring model (this is the load-bearing part)

### Pipeline
`run(parcels)` executes, in order:
1. **Normalize CRS.** Reproject `parcels` to `measurement_crs` (default EPSG:5070);
   validate/repair geometry. (§ CRS rules below.)
2. **Filter.** Apply every `Filter` in sequence (logical AND). A parcel survives
   only if it passes all. Surviving set = `S`.
3. **Score.** For each `Criterion` compute a raw per-parcel value over `S`,
   normalize to `[0,1]` (§ Normalization), apply `prefer` direction.
4. **Combine.** `score = 100 · Σ_i (w'_i · signal_i)`, where `w'_i` are
   weight-normalized (§ Weights). Record each term as a breakdown contribution.
5. **Rank.** Sort by `score` descending; ties broken by original parcel index
   (stable, reproducible). `rank` is 1-based, 1 = best.

### Weights (FR-1)
- Weights auto-normalize: `w'_i = w_i / Σ_j w_j`. Σ `w'_i` = 1.0.
- All weights ≤ 0, or empty `score` list → clear `ValueError`.

### Normalization — min-max across survivors (FR-3)
For a criterion's raw values `r` over `S`:
- `norm(r) = (r - min(r)) / (max(r) - min(r))`.
- **Degenerate range** (`max == min`, incl. `|S| == 1`): every parcel gets `0.5`
  (neutral — the criterion cannot discriminate, so it neither rewards nor penalizes).
- **Missing values:** a parcel with `NaN` raw value gets `signal = 0` (treated as
  worst on that criterion), and is excluded from the min/max computation.
- **`prefer` direction:** `"near"`/`"low"` → `signal = 1 - norm`; `"far"`/`"high"`
  → `signal = norm`. (`Gap` always behaves as `"low"`; reward scarcity.)

> Rationale: min-max over the candidate set is the standard, explainable choice
> and keeps scores relative to *the parcels under consideration* — the analyst's
> actual decision set. No external reference data needed (BYO-data, principle 2).

### Breakdown (FR-4)
`score_breakdown` is a per-parcel `dict[str, float]` of
`{criterion_name: 100 · w'_i · signal_i}`. **MUST** sum (within float tolerance)
to that parcel's `score`. Default `criterion_name` = class name, deduped with a
numeric suffix when a strategy repeats a criterion type (e.g. `Proximity`,
`Proximity_2`); an explicit `name=` overrides.

## Filters (v0.1) — FR-2
Each drops parcels failing its predicate; all computed in the measurement CRS.
- `MinArea(acres)` / `MaxArea(acres)` — area via metric CRS, m² → acres `÷ 4046.8564224`.
- `NotWithin(layer)` — drop parcels intersecting any geometry in `layer`.
- `Within(layer)` — keep only parcels intersecting `layer`.
- `AttrIn(field, values)` — keep `parcel[field] ∈ values`.
- `AttrRange(field, min=None, max=None)` — keep `min ≤ parcel[field] ≤ max`
  (each bound optional). Missing `field` → `KeyError` with a clear message.

## Criteria (v0.1)
Each yields one raw value per parcel; the engine normalizes it.
- `Proximity(to, weight, prefer="near")` — raw = distance (m) to nearest geometry
  in `to`. Empty `to` → `ValueError`.
- `Gap(of, within_mi, weight)` — raw = count of points in `of` within `within_mi`
  (→ meters) of the parcel; normalized as `prefer="low"` (reward gaps).
- `Index(layer, weight, value_field=None, prefer="high")` — score from an index:
  if `layer` is a `str`, use that column already on the parcels; if a
  `GeoDataFrame`, spatial-join parcels → `layer` and read `value_field` (required
  for a multi-column layer; if the layer has exactly one non-geometry numeric
  column, default to it).
- `AttrValue(field, weight, prefer="high")` — raw = numeric `parcel[field]`.

## CRS rules (folds in spec: crs-handling) — FR-6
- `to_measurement_crs(gdf, crs=EPSG:5070)`: reproject; repair geometry with
  `make_valid`. `gdf.crs is None` → `ValueError` ("set a CRS first; unknown CRS
  cannot be measured safely").
- `ensure_aligned(*gdfs, crs)`: reproject each to `crs`; `warnings.warn` for every
  input whose original CRS differed. Layers in filters/criteria pass through this
  before any spatial op — **never silently joined** across CRSs.

## Export — FR-7
- `Result.to_file(path)`: `.geojson`/`.json` → GeoJSON (reproject to EPSG:4326 for
  portability, the GeoJSON standard); `.parquet` → GeoParquet (keep measurement
  CRS). `score_breakdown` serialized as a JSON string column. Unknown extension →
  `ValueError`.
- `Result.top(n=20)` → the `n` highest-ranked parcels (a `GeoDataFrame`).

## Result columns
The `Result.parcels` frame = surviving input columns **plus**: `score` (float
0–100), `rank` (int), `score_breakdown` (dict, or JSON string once exported), and
one `signal__<criterion_name>` column per criterion (the post-`prefer` `[0,1]`
signal, for inspection/debugging).

## Success criteria (testable)
- **SC-1 (FR-3/FR-4):** On a hand-built fixture, engine score == hand-computed
  overlay (± 1e-6), and `Σ score_breakdown == score` for every parcel.
- **SC-2 (FR-2):** Survivor set after filters matches a manual predicate check.
- **SC-3 (FR-1):** Empty `score`, all-zero weights, and unknown field raise clear errors.
- **SC-4 (FR-3):** Area in acres correct on a known-area polygon (± 0.1%).
- **SC-5 (FR-5):** `rank`/`top(n)` order is monotonically non-increasing in score.
- **SC-6 (FR-6):** A WGS84 input is reprojected and measured correctly; a
  no-CRS input raises; a mismatched layer warns.
- **SC-7 (FR-7):** Round-trip export → re-read keeps survivors, scores, and ranks.

## Assumptions
- Inputs are vector `GeoDataFrame`s with valid (or repairable) geometry.
- `measurement_crs` is an equal-area or local projected CRS (default 5070 = CONUS).
- Parcels are polygons; criteria layers may be points, lines, or polygons.

## Open questions
- Min-max vs. percentile-rank normalization if a user wants outlier robustness —
  defer; min-max is the v0.1 contract, revisit with real demo data.
