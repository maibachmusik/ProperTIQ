# Spec 005 — Documentation Site

**Status:** ready to implement · **Milestone:** v0.3 (brought forward) · PRD §10, N-7.

## Summary
A mkdocs-material docs site that reads as a tool: overview, quickstart, concepts
(the scoring model + CRS), a **blocks reference auto-generated from the
registry**, the declarative-YAML guide, the no-code config-app guide, examples,
and an auto API reference. Building it is part of CI hygiene.

## Goals
- `mkdocs build --strict` passes (no broken links/refs).
- The block/tooltip reference is **generated from `propertiq.registry`** at build
  time — same single source of truth as the engine and the app; it cannot drift.
- API reference auto-rendered from docstrings (mkdocstrings).

## Non-goals
- Hosting/deploy automation beyond an optional gh-pages workflow. Versioned docs
  (mike/mike). A custom theme.

## Pages (nav)
- **Home** — what/why, the 10-line promise.
- **Quickstart** — install, a runnable Python example, what you get back.
- **Concepts** — Strategy/Filter/Criterion, the scoring math (min-max, weights,
  breakdown), CRS handling.
- **Blocks reference** — *generated*: every filter & criterion with its
  description and each parameter's tooltip, straight from the registry.
- **Declarative strategies (YAML)** — the config format + round-trip.
- **Config app** — the no-code builder (links `app/README.md`).
- **Examples** — the worked notebooks.
- **API reference** — mkdocstrings over `propertiq`.
- **Scope (PRD)** — the existing `docs/PRD.md`.

## Functional requirements
| ID | Requirement | Acceptance |
|---|---|---|
| FR-D1 | `mkdocs build --strict` succeeds | Exit 0, no warnings-as-errors |
| FR-D2 | Blocks page generated from registry | Every registry block + param tooltip appears; a test/build regenerates it |
| FR-D3 | API reference renders from docstrings | `propertiq` public API present |
| FR-D4 | `[docs]` extra installs the toolchain | mkdocs-material, mkdocstrings[python], mkdocs-gen-files |

## Success criteria
- **SC-D1:** `mkdocs build --strict` exits 0 in a clean checkout with `[docs]`.
- **SC-D2:** The generated blocks page contains every block key and every
  parameter `help` string from the registry (verified by a content check).
- **SC-D3:** Internal nav links resolve (strict mode enforces this).

## Assumptions
- mkdocs-gen-files runs `scripts/gen_blocks.py` to emit the blocks page at build.
- The site is not auto-deployed yet; a gh-pages workflow can be added later.
