# Tasks 001 — Scoring Core (v0.1)

Order = dependency order. Each task is independently testable.

- [ ] **T1 — CRS module.** Implement `to_measurement_crs` (reproject + `make_valid`,
  raise on `crs is None`) and `ensure_aligned` (reproject each, warn on mismatch).
  → SC-4, SC-6.
- [ ] **T2 — Engine base + helpers.** In `strategy.py`: add `name`/`prefer` to
  `Criterion`, a `raw()` hook; implement `_normalize_weights`, `_minmax`
  (degenerate→0.5, NaN→excluded/signal 0), `_apply_prefer`, `_resolve_names`.
- [ ] **T3 — Filters.** Implement `apply()` for MinArea, MaxArea, NotWithin,
  Within, AttrIn, AttrRange (align layers, area in acres). → SC-2.
- [ ] **T4 — Criteria.** Implement `raw()` for Proximity, Gap, Index, AttrValue
  (align layers, distance/density/join/attr). → SC-1.
- [ ] **T5 — Strategy.run + Result.** Wire the 5-step pipeline; build `score`,
  `rank`, `score_breakdown`, `signal__*` cols; `top()`, `explain()`. → SC-1, SC-5.
- [ ] **T6 — Export.** `io.to_file` + `Result.to_file` (GeoJSON→4326,
  GeoParquet→keep CRS, breakdown→JSON string). → SC-7.
- [ ] **T7 — Tests + fixtures.** `conftest.py` fixture county; `test_crs`,
  `test_filters`, `test_scoring` (incl. hand-computed SC-1 + breakdown sums +
  degenerate/NaN), `test_export`. Keep `test_smoke` green.
- [ ] **T8 — Quality gate.** `ruff`, `mypy`, full `pytest` green. Update
  `__init__` exports if needed. (Version bump to 0.1.0 deferred to exit gate.)

## Consistency check (plan ↔ spec ↔ FR)
FR-1 → T2/T5 · FR-2 → T3 · FR-3 → T2/T4/T5 · FR-4 → T5 · FR-5 → T5 · FR-6 → T1 ·
FR-7 → T6. All v0.1 FRs covered; YAML/viz/loaders correctly deferred.
