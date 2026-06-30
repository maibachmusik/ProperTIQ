# Plan 002 — Strategy Config & Registry

Implements spec 002. Pure-Python over the existing core; no new runtime deps
(PyYAML already a core dep).

## Modules
- **`registry.py`** (new): `ParamSpec`, `BlockSpec` dataclasses; a `REGISTRY`
  list with one `BlockSpec` per public block; accessors `get(key)`, `filters()`,
  `criteria()`, `all_keys()`. Param `type` values: number/integer/text/select/
  multiselect/layer/field/bool. Each `BlockSpec.cls` points at the real class so
  `from_config` instantiates without a separate mapping.
- **`config.py`** (new): `from_config(config, layers=None)` and `to_config(strategy)`.
  - `from_config`: validate top-level keys (`name`,`filters`,`score`); for each
    item `{key: params}` look up the `BlockSpec`, validate param names against its
    `ParamSpec`s, resolve `layer`-typed params via `layers`, build kwargs, instantiate.
  - `to_config`: reverse — read each instance's fields per its `ParamSpec`s; emit
    layer params as their layer name (requires a reverse `layers` lookup by identity,
    or the instance stores the name — see below).
- **`strategy.py`**: add `Strategy.to_config(layer_names=None)` delegating to
  `config.to_config`. Keep engine untouched.
- **`io.py`**: implement `load_strategy(path, layers=None)` (YAML→`from_config`)
  and add `dump_strategy(strategy, path)` (config→YAML). Wire package `run()` to
  accept a dict or path.

## Layer round-trip detail
`to_config` needs to turn a layer object back into its name. Approach: callers
pass `layer_names: dict[id->name]` OR (simpler) the app/notebook builds config
directly from its form (it already knows names) — so `to_config` is best-effort:
if a `layer_names` map is given, use it; else emit a placeholder `"<layer>"` and
warn. Primary round-trip path for the app is form→config (not object→config), so
`session_to_config` (spec 003) is the authoritative serializer; `to_config` is a
convenience. Document this.

## Registry content (the tooltips — plain language, owner-facing)
One entry each: `min_area`, `max_area`, `not_within`, `within`, `attr_in`,
`attr_range` (filters); `proximity`, `gap`, `index`, `attr_value` (criteria).
Every `ParamSpec.help` is a one-sentence, non-technical explanation (e.g.
proximity.to → "The map layer to measure distance to (e.g. highways)."). Keys
match the YAML names already shown in the PRD §4 declarative example.

## Tests (`tests/test_registry.py`, `tests/test_config.py`)
- Drift: `REGISTRY` keys ≡ the set of public Filter/Criterion subclasses exported
  from `propertiq` (SC-C2). Reflect over `__all__`.
- Metadata completeness: every BlockSpec has label+description; every ParamSpec
  has label+help (non-empty) (SC-C4).
- Round-trip: build a Strategy via YAML + `layers`, compare scores to the Python
  equivalent on the fixture county (SC-C1). dict ↔ YAML ↔ scores.
- Errors: unknown key, unknown param, missing layer name → clear raises (SC-C3).

## Out of scope
The app (003). Any widget code. Drive-time/raster blocks.
