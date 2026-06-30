# Tasks 003 — Standalone Config App

- [ ] **T1 — packaging.** `app/__init__.py`; `[app]` extra (streamlit,
  streamlit-folium, folium); `pytest pythonpath=["."]`. → FR-A1.
- [ ] **T2 — _logic.py.** `session_to_config`, `config_to_session`,
  `param_widget_spec`, `new_block_state`, block accessors. → FR-A2..A5, A8.
- [ ] **T3 — strategy_builder.py.** Streamlit UI: upload data, add blocks with
  registry tooltips, run, show table/explain/map, export results + YAML, load
  YAML. Import-safe (UI under `main()`). → FR-A1..A8.
- [ ] **T4 — tests.** `test_app_logic.py`: SC-A1 (state→config→run scores),
  SC-A2 (every param tooltip), SC-A3 (state round-trip), SC-A4 (import-safe),
  widget-options.
- [ ] **T5 — app/README.md.** How to install `[app]` and `streamlit run`.
- [ ] **T6 — gate.** ruff + mypy + pytest green; manual `streamlit run` smoke (SC-A5).

## Consistency check
FR-A1→T1/T3 · FR-A2..A5→T2/T3 · FR-A6→T3 · FR-A7→T3 · FR-A8→T2/T3. SC-A1..A4→T4.
