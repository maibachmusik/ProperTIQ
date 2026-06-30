# Tasks 005 — Documentation Site

- [x] **T1 — toolchain.** `[docs]` extra (mkdocs-material, mkdocstrings[python],
  mkdocs-gen-files); `mkdocs.yml` (material theme, nav, plugins). → FR-D4.
- [x] **T2 — pages.** index, quickstart, concepts (scoring math + CRS), yaml,
  config-app, examples; `api.md` via mkdocstrings. → FR-D3.
- [x] **T3 — generated blocks page.** `scripts/gen_blocks.py` emits `blocks.md`
  from `propertiq.registry` at build (mkdocs-gen-files). → FR-D2.
- [x] **T4 — verify.** `mkdocs build --strict` exits 0; generated page contains
  every block key + param tooltip; API ref renders. → SC-D1..D3.
- [x] **T5 — CI.** Add a `docs` job running `mkdocs build --strict`.

## Consistency check
FR-D1→T4/T5 · FR-D2→T3/T4 · FR-D3→T2/T4 · FR-D4→T1. SC-D1..D3 verified in T4.
