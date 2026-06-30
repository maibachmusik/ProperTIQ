# Spec 004 — Result Visualization (`to_map`)

**Status:** ready to implement · **Milestone:** v0.2 · **Covers:** FR-9 (`.to_map()`).
**Constitution:** principles 1 (explainable), 5 (open formats), 6 (thin core).

## Summary
`Result.to_map()` returns an interactive **folium** map of the scored candidates,
colored by score, with a tooltip per parcel showing its score, rank, and the
per-criterion breakdown. folium is the core engine (PRD N-4); leafmap stays an
optional `[viz]` nicety for later.

## Goals
- One call, sensible defaults: `result.to_map()` → a `folium.Map` ready to display
  in a notebook or embed.
- Color by any numeric column (default `score`), on a fixed, meaningful scale.
- Tooltip exposes *why* (the breakdown) — keeps the no-black-box promise on the map.

## Non-goals
- leafmap rendering, basemap galleries, layer toggles for input layers, raster.
- Saving to HTML (the caller can `m.save(...)`; folium already does that).

## API
```python
Result.to_map(
    column: str = "score",      # numeric column to color by
    n: int | None = None,        # only the top-n candidates (None = all survivors)
    cmap: str = "YlGn",          # higher = better/greener
    tiles: str = "CartoDB positron",
    tooltip_fields: list[str] | None = None,  # extra columns to show
) -> folium.Map
```

## Behavior
- Reproject candidates to **EPSG:4326** for web display.
- Color scale: if `column == "score"`, fix the domain to **0–100** (scores are
  absolute); otherwise min–max over the shown candidates. Use a `branca`
  colormap; add it as a legend.
- Tooltip always includes `rank`, `score`, then any `tooltip_fields`. The
  `score_breakdown` is shown as a readable `criterion: contribution` list.
- Center/zoom fit the candidates' bounds (computed from `total_bounds`, not a
  geographic centroid, to avoid CRS-mean warnings).
- Polygons render filled; points/lines render with markers/paths in the same color.
- **Empty result → clear `ValueError`** ("no candidates to map").
- **Missing `column` → clear `KeyError`.**
- folium not importable → `ImportError` with the install hint (`propertiq[viz]`/core).

## Success criteria
- **SC-V1:** On a fixture result, `to_map()` returns a `folium.Map` with ≥1 GeoJson
  layer and no exception.
- **SC-V2:** `to_map(column="acres")` works on a non-score numeric column.
- **SC-V3:** Empty result → `ValueError`; unknown column → `KeyError`.
- **SC-V4:** Rendered HTML (`m._repr_html_()`) contains the score values (tooltip
  wired) — a smoke that the data reached the map.

## Assumptions
- folium becomes a **core dependency** (PRD N-4 "folium core"). Candidates carry
  `score`, `rank`, `score_breakdown` (guaranteed by the engine).
