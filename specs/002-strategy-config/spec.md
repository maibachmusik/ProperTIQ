# Spec 002 — Strategy Config & Block Registry (v0.2)

**Status:** ready to implement · **Milestone:** v0.2 · **Covers:** FR-1, FR-8 (brought
forward), and the schema foundation the config app (spec 003) needs.
**Constitution:** principles 1, 4, 6.

## Summary
Make strategy rules **manipulable as data, not code**, and give the system one
**source of truth** describing every filter and criterion. A `registry` catalogs
each block with human metadata (label, plain-language description, per-parameter
help/tooltips, types, defaults, options). From it we get: (1) a config
`dict`/YAML ↔ `Strategy` round-trip, (2) validation, and (3) the form schema +
tooltips the config app renders — so **tooltips can never drift from behavior**,
because the app and the engine read the same registry.

## Why
- The owner needs deployment-specific rules editable by non-coders (per the
  amended PRD non-goal) without touching Python.
- Tooltips in the app must match what each block actually does. The only robust
  way is to derive both the app form and its help text from library-owned
  metadata, not hand-written app copy.

## Goals
- A declarative `registry` of all public filters + criteria, each with a stable
  `key` (YAML name), `label`, `description`, and ordered `params` (each with
  `type`, `label`, `help`, `default`, and `options`/bounds where relevant).
- `from_config(config, layers=None)` builds a `Strategy`; `Strategy.to_config()`
  serializes one back. YAML load/dump via `io`.
- Registry **completeness is enforced**: every public block has a registry entry
  and vice-versa (a test fails on drift).

## Non-goals
- The app UI itself (spec 003). Drive-time / raster blocks (later). Auth, persistence.

## User scenarios
- **P1:** A YAML/dict strategy round-trips to an identical `Strategy` and produces
  identical scores to the equivalent Python (`FR-8`).
- **P2:** A tool (the config app, or a notebook) reads `registry` to list
  available blocks and render each parameter with its tooltip — no hard-coded copy.

## Key entities
- **`ParamSpec`**: `name`, `type` ∈ {`number`,`integer`,`text`,`select`,
  `multiselect`,`layer`,`field`,`bool`}, `label`, `help` (tooltip), `default`,
  `options` (for select/multiselect), `min`/`max` (numeric), `required`.
  - `type="layer"` → value is the **name** of a user-supplied GeoDataFrame
    (resolved via the `layers` map). `type="field"` → a column name on the parcels.
- **`BlockSpec`**: `key`, `kind` ∈ {`filter`,`criterion`}, `cls`, `label`,
  `description`, `params: list[ParamSpec]`.
- **`registry`**: ordered list of `BlockSpec`, with `get(key)` / `filters()` /
  `criteria()` accessors.

## Config format (canonical)
```yaml
name: rv_storage
filters:
  - min_area: {acres: 3}
  - attr_in:  {field: zoning, values: [industrial, commercial]}
score:
  - proximity: {to: highways, weight: 0.30, prefer: near}
  - gap:       {of: storage_pois, within_mi: 5, weight: 0.25}
```
- Each list item is a single-key dict: `{block_key: {param: value}}`.
- `layer`-typed params hold a **layer name** (str); `from_config(..., layers={...})`
  resolves names → GeoDataFrames. A missing layer name → clear `KeyError` listing
  available layer names.
- Unknown `block_key` or unknown param → clear `ValueError` naming the offender.

## Functional requirements
| ID | Requirement | Acceptance |
|---|---|---|
| FR-C1 | `registry` lists every public filter + criterion with full metadata | Drift test passes: registry keys ≡ public blocks |
| FR-C2 | `from_config(config, layers)` → `Strategy` | Round-trips; resolves layer names; clear errors on bad keys |
| FR-C3 | `Strategy.to_config()` → dict | `from_config(s.to_config())` reproduces the strategy |
| FR-C4 | YAML load/dump (`io.load_strategy`, `io.dump_strategy`) | YAML ≡ dict ≡ Python; scores identical (FR-8) |
| FR-C5 | Every `ParamSpec` carries a non-empty `help` tooltip | Test: no block/param has empty label or help |

## Success criteria
- **SC-C1:** A YAML strategy and its Python equivalent produce identical `score`
  and `rank` on the fixture county (± 1e-9).
- **SC-C2:** `registry` covers all 6 filters + 4 criteria; adding a new block
  without a registry entry fails the drift test.
- **SC-C3:** Bad config (unknown key, unknown param, missing layer) raises a clear,
  named error.
- **SC-C4:** Every param has a human `label` and non-empty `help`.

## Assumptions
- Layer-typed params reference layers by name; the caller provides the `layers` map
  (the app from uploads, a notebook from its own variables).
- `prefer`/`values`/`within_mi` etc. validate against the registry's param specs.

## Open questions
- Whether to expose per-block JSON Schema for external tooling — defer; the
  `registry` dataclasses are the contract for now.
