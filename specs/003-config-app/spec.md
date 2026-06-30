# Spec 003 — Standalone Config App (no-code strategy builder)

**Status:** ready to implement · **Milestone:** v0.2 · **Depends on:** spec 002.
**Constitution:** principles 1, 2, 5 (app is a thin client over the GUI-free core).

## Summary
A **standalone companion app** (separate deployable, not part of the core
library) that lets a non-technical user **build, edit, run, and export a scoring
strategy without writing code** — for any deployment/vertical. Every filter and
criterion offered, and every tooltip explaining it, is rendered **from the
`registry` (spec 002)**, so what the user sees always matches what the engine
does. The app produces a config the core runs and can export that config (YAML)
for reuse.

## Why
Owner decision: deployments will be configured by non-coders. They need to (a)
understand each rule (matching tooltips), (b) compose a strategy from the
building blocks, (c) run it on their parcels, and (d) save/share the result and
the strategy. The app is the configuration surface; the library is the engine.

## Goals
- Upload parcels + named layers; build a strategy from registry blocks via forms.
- **Every input has a tooltip sourced from the registry** — block descriptions and
  per-parameter help. No hand-written, drift-prone copy in the app.
- Run the strategy and show: ranked candidates table, per-criterion `explain`
  breakdown, and an interactive map.
- Export results (GeoJSON/GeoParquet) **and** the strategy config (YAML).
- Load a previously-saved strategy YAML back into the builder.

## Non-goals (this spec)
- Auth, multi-user, hosting/ops, a database. (Single-session, local/standalone.)
- New scoring logic — the app only composes existing blocks.
- Bundling any data (constitution 2) — user brings parcels/layers.

## User scenarios (prioritized)
- **P1 (MVP):** A user opens the app, uploads a parcels file, adds *Min area* and
  *Allowed zoning* filters and two scoring criteria (each chosen from a labeled
  list with tooltips), sets weights, clicks **Run**, and sees ranked parcels +
  map. Exit: a non-coder produces a scored, ranked map from their own data.
- **P2:** They click **Export strategy** → a YAML file; later they **Load** it and
  the builder repopulates identically.
- **P3:** They export the scored candidates to GeoJSON.

## Functional requirements
| ID | Requirement | Acceptance |
|---|---|---|
| FR-A1 | Upload parcels (GeoJSON/GeoParquet) + ≥0 named layers | Files load to GeoDataFrames; layer names usable in `layer` params |
| FR-A2 | Pick blocks from registry, grouped Filters / Scoring | List shows `label`; selecting shows `description` |
| FR-A3 | Render each param as the right widget **with its registry `help` tooltip** | Every input has a tooltip; widget type matches `ParamSpec.type` |
| FR-A4 | `layer`/`field` params populate from uploaded layers / parcel columns | Dropdowns list real names; no free-text guessing |
| FR-A5 | Build config from the form and run via `propertiq` core | Uses `from_config` + `Strategy.run`; errors surfaced readably |
| FR-A6 | Show ranked table, `explain` breakdown, interactive map | Top-N table, contributions sum to score, map renders |
| FR-A7 | Export results (GeoJSON/GeoParquet) and strategy (YAML) | Files download; YAML reloads (FR-A8) |
| FR-A8 | Load a strategy YAML back into the builder | Builder state matches the file |

## Architecture
- **Separate package/deployable** in `app/` with its own optional dependency group
  `[app]` (streamlit, streamlit-folium, leafmap). The core `propertiq` wheel does
  **not** depend on it; installing the app pulls the core.
- `app/strategy_builder.py` (Streamlit). Pure, testable helpers live in
  `app/_logic.py`: `session_to_config(state) -> dict`, `config_to_session(dict)`,
  `param_widget_spec(ParamSpec)` — unit-tested headless (no Streamlit runtime).
- All block lists, labels, and tooltips come from `propertiq.registry`. The app
  contains **zero** hard-coded descriptions of blocks.

## Success criteria
- **SC-A1:** Headless test: a simulated builder state → `session_to_config` →
  `from_config` → `Strategy.run` reproduces the fixture-county scores.
- **SC-A2:** Every registry param maps to a widget spec with a non-empty tooltip
  (no missing/empty help) — asserted in a test over the whole registry.
- **SC-A3:** `config_to_session(session_to_config(state)) == state` (round-trip).
- **SC-A4:** App module imports without a running Streamlit server (import-safe).
- **SC-A5 (manual):** `streamlit run` launches; build→run→export works end-to-end.

## Assumptions
- Streamlit is acceptable for the standalone app (fastest path; can move to its
  own repo later without touching the core). Owner chose a standalone app form.
- Map via `streamlit-folium`; large layers are the user's responsibility (no
  server-side tiling).

## Open questions
- Multi-strategy management / saved-library UI — defer to a later iteration; v1
  is single-strategy build/run/export.
