# Plan 001 — Scoring Core (v0.1)

Implements `spec 001`. Stack per PRD §3 (resolved): Python 3.10+, geopandas /
shapely 2 / pyproj, pytest + a fixture county, hatchling, ruff + mypy.

## Module responsibilities (matches PRD §5 scaffold)
- **`crs.py`** — `to_measurement_crs`, `ensure_aligned`. Geometry repair via
  `GeoSeries.make_valid()` (shapely 2). Reproject with `gdf.to_crs()`.
- **`strategy.py`** — engine. `Filter`/`Criterion` base classes already define
  `apply()` / `score()`. Add to base classes:
  - `Criterion`: `weight`, `prefer`, `name` attrs; a `raw(parcels, crs)` →
    `pd.Series` that subclasses implement; base `score()` stays the normalized
    public hook but the engine drives `raw → normalize → prefer`.
  - `Strategy.run()` orchestrates the 5-step pipeline; returns `Result`.
  - Helpers (module-private): `_normalize_weights`, `_minmax(series)` (handles
    degenerate range → 0.5, NaN → excluded then signal 0), `_resolve_names`.
  - `Result.top`, `Result.explain` (simple DataFrame for v0.1), `Result.to_file`.
- **`filters.py`** — each dataclass implements `apply(parcels) -> GeoDataFrame`.
  Area filters use `parcels.geometry.area` (m² in measurement CRS). `NotWithin`/
  `Within` use `gpd.sjoin(predicate="intersects")` on the (CRS-aligned) layer,
  then keep/drop by join membership.
- **`scoring.py`** — each dataclass implements `raw(parcels, crs) -> pd.Series`:
  - `Proximity`: `parcels.geometry.distance(layer.union_all())` after aligning
    `to`; or `gpd.sjoin_nearest` for speed — use `sjoin_nearest` (returns
    distance via `distance_col`), fall back to `distance(union_all())` if needed.
  - `Gap`: build the parcel buffer? No — count points within radius via
    `sjoin` of `of` points to `parcels.buffer(within_mi*1609.344)`, group-count.
  - `Index`: `str` → `parcels[col]`; `GeoDataFrame` → `gpd.sjoin(parcels, layer,
    predicate="intersects")` then take `value_field` (resolve single numeric col).
  - `AttrValue`: `parcels[field]` as float.
- **`io.py`** — `to_file` dispatch by extension (GeoJSON→4326, GeoParquet→keep
  CRS); leave `load_strategy` as `NotImplementedError` (v0.2, spec 003).

## Engine detail — `Strategy.run`
```
gdf = to_measurement_crs(parcels, measurement_crs)
for f in filters: gdf = f.apply(gdf)            # may align layers internally
if score is empty or Σweight<=0: raise ValueError
weights = _normalize_weights(score)
contribs = {}                                    # name -> 100*w'*signal Series
for crit, w in zip(score, weights):
    raw = crit.raw(gdf, measurement_crs)
    sig = _apply_prefer(_minmax(raw), crit.prefer)   # Gap forces "low"
    gdf[f"signal__{name}"] = sig
    contribs[name] = 100 * w * sig
score_series = sum(contribs.values())
gdf["score"] = score_series
gdf["score_breakdown"] = [ {n: contribs[n].iloc[i] ...} per row ]
gdf = gdf.sort_values("score", ascending=False, kind="stable")
gdf["rank"] = range(1, len(gdf)+1)
return Result(parcels=gdf, strategy=self)
```
Name resolution: `_resolve_names(score)` → class name, dedupe repeats with
`_2`, `_3`; explicit `name=` wins. Store back on each criterion for breakdown keys.

## Layer alignment
Every filter/criterion that takes a `layer`/`to`/`of` GeoDataFrame calls
`ensure_aligned(layer, crs=measurement_crs)` at the top of its `apply`/`raw`, so a
mismatched-CRS layer warns once and is reprojected — never silently joined
(constitution 3). Empty layer where one is required → `ValueError`.

## Edge cases to cover in code
- Empty survivor set after filters → `Result` over an empty frame; `top`/`explain`/
  `to_file` handle 0 rows without raising; score columns still present.
- Single survivor → every criterion degenerate → `score == 50.0` (all 0.5).
- `NaN` in an attribute criterion → excluded from min/max, signal 0.
- `sjoin_nearest` requires shapely 2 + geopandas ≥0.10 (have ≥0.14, fine).

## Testing (pytest, `tests/`)
- `conftest.py`: a tiny **fixture county** — a handful of square parcels in a
  projected CRS with known areas, plus point/line layers (a "highway" line, two
  competitor points, a floodplain polygon). Deterministic, no network.
- `test_crs.py` (SC-4, SC-6), `test_filters.py` (SC-2), `test_scoring.py`
  (SC-1, SC-3, SC-5 + breakdown-sums + degenerate/NaN), `test_export.py` (SC-7).
- Keep existing `test_smoke.py` green (construction + version).
- Hand-compute one full strategy by hand in `test_scoring.py` to pin SC-1.

## Tooling / CI
- `ruff check` + `ruff format`, `mypy src/propertiq`, `pytest -q` all green.
- Existing `.github/workflows/ci.yml` should run them on 3.10/3.11/3.12.
- Bump `pyproject` version `0.0.1.dev0 → 0.1.0` only at the v0.1 exit gate.

## Out of scope here (later specs)
YAML loader (003), `.to_map()` folium render, `loaders/`, drive-time, raster.
