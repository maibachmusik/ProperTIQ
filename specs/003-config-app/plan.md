# Plan 003 — Standalone Config App

Implements spec 003. Streamlit app in `app/`, kept out of the core wheel; depends
on `propertiq` + spec 002's `registry`/`config`. **Zero hard-coded block copy** —
every label/tooltip comes from `propertiq.registry`.

## Layout
```
app/
  __init__.py
  _logic.py            pure, Streamlit-free, unit-tested
  strategy_builder.py  the Streamlit UI (imports _logic + streamlit lazily)
  README.md            how to run it
```
- `[app]` optional-dependency group: streamlit, streamlit-folium, folium.
- `pyproject` `[tool.pytest.ini_options] pythonpath=["."]` so tests import `app`.

## `_logic.py` (the testable core)
- **State model** (plain dict, what the UI edits):
  ```
  {"name": str,
   "filters": [{"key": "min_area", "params": {"acres": 3}}, ...],
   "score":   [{"key": "proximity", "params": {"to": "highways", "weight": .3, "prefer": "near"}}, ...]}
  ```
- `session_to_config(state) -> dict` — reshape to canonical config
  (`{key: params}` items), dropping unset optional params.
- `config_to_session(config) -> state` — inverse (for loading a YAML back).
- `param_widget_spec(param, *, layer_names, field_names) -> dict` — resolve a
  `ParamSpec` to a concrete widget descriptor `{kind,label,help,default,options}`;
  `layer`→options=layer_names, `field`→options=field_names, select/multiselect→
  param.options. **help is always carried through** (tooltip).
- `new_block_state(block_key) -> dict` — default params from the registry.
- `available_blocks()` — `registry.filters()` / `registry.criteria()` passthrough.

## `strategy_builder.py` (UI, thin)
Sidebar: upload parcels (GeoJSON/GeoParquet) + add named layers (name + file).
Main: strategy name; two sections (Filters, Scoring) where the user adds blocks
from a selectbox (labels from registry, `help=description`); each block renders
its params via `param_widget_spec`, every `st.*` input gets `help=spec['help']`.
Run → `from_config(session_to_config(state), layers) .run(parcels)`; show
`st.dataframe(result.top(n))`, `result.explain()`, and a `streamlit_folium` map.
Buttons: export results (GeoJSON/GeoParquet via `result.to_file`), export
strategy YAML (`dump_strategy`/`session_to_config`+yaml), and load a YAML
(`config_to_session`). All UI code lives under `def main()`, called from
`if __name__ == "__main__"` so plain import is side-effect-free (SC-A4).

## Tests (`tests/test_app_logic.py`, headless — no Streamlit runtime)
- SC-A1: a hand-built state → `session_to_config` → `from_config(layers)` → run →
  fixture-county scores match the Python equivalent.
- SC-A2: every registry param → `param_widget_spec` has non-empty `help`.
- SC-A3: `config_to_session(session_to_config(state)) == state`.
- SC-A4: `import app.strategy_builder` runs no Streamlit calls (import-safe).
- layer/field widget specs carry the provided names as options.

## Out of scope
Auth, persistence, multi-strategy library, hosting. Manual `streamlit run` smoke
(SC-A5) documented in `app/README.md`.
