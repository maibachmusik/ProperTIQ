# Contributing to ProperTIQ

Thanks for your interest! ProperTIQ stays small and composable. The most useful
contributions are **new filters** and **new scoring criteria** — each is a small,
self-contained, testable unit.

## Adding a filter
1. Subclass `Filter` in `src/propertiq/filters.py`.
2. Implement `apply(parcels) -> GeoDataFrame` (drop non-qualifying rows).
3. Add a unit test against the fixture county in `tests/`.

## Adding a scoring criterion
1. Subclass `Criterion` in `src/propertiq/scoring.py`.
2. Implement `score(parcels) -> Series` normalized to `[0, 1]`.
3. Add a unit test; verify the contribution appears in `score_breakdown`.

## Principles (the constitution)
- Explainable scoring — no black boxes; everything decomposes.
- Bring-your-own-data — never bundle or host parcel data.
- Metric CRS for all area/distance math, with geometry validation.
- Small, well-typed surface over a thin geopandas core.

## Dev setup
```bash
pip install -e ".[dev,viz]"
pre-commit install
pytest
```
