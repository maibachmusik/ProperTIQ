# Tasks 002 — Strategy Config & Registry

- [ ] **T1 — registry.py.** `ParamSpec`, `BlockSpec`, `REGISTRY` (all 10 blocks
  with labels, descriptions, per-param help/tooltips), accessors. → FR-C1, FR-C5.
- [ ] **T2 — config.py.** `from_config(config, layers)` (validate, resolve layers,
  instantiate) + `to_config(strategy, layer_names=None)`. → FR-C2, FR-C3.
- [ ] **T3 — io + run wiring.** `io.load_strategy`/`io.dump_strategy`;
  `propertiq.run(dict|path, parcels, layers=)`; export from `__init__`. → FR-C4.
- [ ] **T4 — tests.** `test_registry.py` (drift + metadata completeness),
  `test_config.py` (YAML≡Python scores, dict↔YAML, error cases). → SC-C1..C4.
- [ ] **T5 — gate.** ruff + mypy + full pytest green.

## Consistency check (FR ↔ task)
FR-C1→T1 · FR-C2→T2 · FR-C3→T2 · FR-C4→T3 · FR-C5→T1. SC-C1..C4 → T4.
