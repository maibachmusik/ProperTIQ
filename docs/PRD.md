# ProperTIQ — Product Requirements Document (scope)

**Site suitability as code.**
**Version:** 1.0 (scope finalized) · **Status:** ready to implement toward `v0.1`
**Package:** `propertiq` · **Repo:** `maibachmusik/ProperTIQ` · **License:** MIT
**Last updated:** 2026-06-29

---

## 0. SDD framing
This is the product-level spec. It feeds the spec-driven-development chain:
`PRD (this doc) → constitution.md → spec.md (per epic) → plan.md → tasks.md → implement`.
It's a living document — change it here first, then regenerate plan and tasks.

---

## 1. What we're building (plain language)
A small Python **library** that other people install (`pip install propertiq`) and use in their own
code or notebooks. You give it **(1) parcels** (land polygons you already have) and **(2) a strategy**
(your rules for what makes land good for a purpose). It returns those parcels **scored 0–100 and
ranked**, with a transparent breakdown of *why* each scored what it did.

A **strategy** has two kinds of rules:
- **Hard filters** — pass/fail (e.g. "≥ 3 acres", "not in a floodplain"). Failing parcels are dropped.
- **Weighted scoring** — soft signals summed to a score (e.g. "closer to highway, weight 0.30").

ProperTIQ owns the **method**, not the data. It scores whatever parcels/layers you bring. That is what
makes it free to give away and dissolves the data-moat problem that the paid tools rely on.

---

## 2. Goals & non-goals

### Goals (v1)
- Compose a `Strategy` from filters + weighted criteria, or load it from YAML.
- `Strategy.run(parcels)` → a result with `score (0–100)`, `rank`, and `score_breakdown`.
- A small, composable library of filters and scoring criteria.
- Correct geometry handling: reproject to a metric CRS for area/distance, validate, warn on mismatch.
- Explainability (`.explain()`), quick map (`.to_map()`), and open-format export.
- Two worked notebooks on real open data (RV/boat storage; car wash).

### Non-goals (deliberate "outs")
- ❌ Hosting/serving parcel data (BYO).
- ❌ A nationwide parcel/zoning normalizer (separate project; a maintenance treadmill).
- ❌ A hosted web app or GUI.
- ❌ Skip-tracing / outreach / CRM / valuation / sales forecasting.
- ❌ Raster-first workflows (vector/parcel-centric first; raster criteria can come later).

### Guardrail
If a feature isn't *a new filter, a new scoring criterion, a new loader, or a new export*, it's
probably out of scope.

---

## 3. Resolved decisions
| ID | Decision | Choice | Rationale |
|---|---|---|---|
| N-1 | Name | **ProperTIQ** (repo) / `propertiq` (package) | Owner's call; unifies under the product name |
| N-2 | License | **MIT** | Maximum adoption for a library |
| N-3 | Default measurement CRS | **EPSG:5070** (NAD83 CONUS Albers Equal Area), configurable to per-AOI UTM | Correct, consistent area/distance nationwide |
| N-4 | Visualization | **folium core**, **leafmap as `[viz]` extra** | Keep base install lean |
| N-5 | First demo county | **Larimer County, CO** (verify open parcel+zoning) | Front Range; strong open data |
| N-6 | Python | **3.10+** | Modern typing, broad availability |
| N-7 | Build/test/docs | hatchling · pytest (fixture county) · mkdocs-material · GitHub Actions | Standard, low-friction |
| N-8 | Repo location | standalone **`ProperTIQ`** under `maibachmusik` | OSS best practice (confirm account) |

*(Open: exact casing "ProperTIQ" vs "PropertIQ" to stamp everywhere — owner to confirm.)*

---

## 4. The API (this is the product)

### Pythonic form
```python
import propertiq as pq
import geopandas as gpd

parcels = gpd.read_file("larimer_county_parcels.geojson")

strategy = pq.Strategy(
    filters=[
        pq.MinArea(acres=3),
        pq.NotWithin(fema_floodplain),
        pq.AttrIn("zoning", ["industrial", "commercial", "agricultural"]),
    ],
    score=[
        pq.Proximity(to=highways,   weight=0.30, prefer="near"),
        pq.Gap(of=storage_pois,     within_mi=5, weight=0.25),
        pq.Index(acs_demand_index,  weight=0.25),
        pq.Proximity(to=rv_dealers, weight=0.20, prefer="near"),
    ],
)

result = strategy.run(parcels)
result.top(20); result.explain(); result.to_map(); result.to_file("candidates.geojson")
```

### Declarative form
```yaml
# strategies/rv_storage.yaml
name: rv_storage
filters:
  - min_area:   {acres: 3}
  - not_within: {layer: fema_floodplain}
  - attr_in:    {field: zoning, values: [industrial, commercial, agricultural]}
score:
  - proximity: {to: highways,     weight: 0.30, prefer: near}
  - gap:       {of: storage_pois, within_mi: 5, weight: 0.25}
  - index:     {layer: acs_demand_index, weight: 0.25}
  - proximity: {to: rv_dealers,   weight: 0.20, prefer: near}
```

### Design promises
- Weights auto-normalize to 1.0; scores are 0–100.
- `score_breakdown` is per-parcel `{criterion: contribution}` summing to the score — **no black box**.
- Filters and criteria are independent, testable units; adding one is a small PR (good-first-issue).

---

## 5. Architecture (thin by design)
```
src/propertiq/
  __init__.py    public API surface
  strategy.py    Strategy, Result, run()  — orchestration + scoring engine
  filters.py     MinArea, MaxArea, NotWithin, Within, AttrIn, AttrRange
  scoring.py     Proximity, Gap (inverse density), Index, AttrValue
  crs.py         reproject-to-metric, validate/repair, mismatch warnings
  io.py          GeoDataFrame / GeoJSON / GeoParquet I/O; YAML strategy loader
  viz.py         to_map() (folium; leafmap via [viz]); explain() tables
  loaders/       [v0.3] thin optional helpers: ACS, OSM POIs, FEMA NFHL, 3DEP slope
```
- **Core deps:** geopandas, shapely, pyproj, pyyaml. **`[viz]`:** folium (+ leafmap).
- **CRS rule (first-class):** inputs reprojected to the measurement CRS (default EPSG:5070) for all
  area/distance math; geometry validated (`make_valid`); mismatched-CRS inputs are warned and
  auto-reprojected — **never silently joined.**
- **Data never bundled.** Loaders (v0.3) are conveniences over open sources; everything works with
  BYO GeoDataFrames from day one.

---

## 6. Data for the demos (open only)
| Layer | Source |
|---|---|
| Parcels + zoning | Larimer County / Colorado open GIS portals |
| Demographics (demand index) | US Census ACS + TIGER/Line |
| Roads / POIs / dealers | OpenStreetMap |
| Floodplain | FEMA NFHL |
| Slope | USGS 3DEP DEM |
| Protected land | PAD-US / NCED |

---

## 7. Functional requirements (v0.1 unless noted)
| ID | Requirement | Acceptance |
|---|---|---|
| FR-1 | Compose `Strategy(filters=[...], score=[...])` | Round-trips; invalid configs raise clear errors |
| FR-2 | Hard filters drop non-qualifying parcels | Survivor set matches a manual check |
| FR-3 | Weighted score 0–100 in the measurement CRS | Reproduces a hand-computed overlay; areas correct |
| FR-4 | `score_breakdown` per parcel sums to score | Contributions verified to sum |
| FR-5 | Rank + `.top(n)` | Order monotonic by score |
| FR-6 | CRS normalize + validate + warn | Mismatched-CRS inputs reprojected, not errored |
| FR-7 | Export GeoJSON/GeoParquet (stated CRS) | File has all candidates + scores |
| FR-8 `[v0.2]` | YAML strategy loader `pq.run(path, ...)` | YAML ≡ Python strategy |
| FR-9 `[v0.2]` | `.explain()` + `.to_map()` | Table + interactive map render |
| FR-10 `[v0.3]` | `loaders/` for ACS/OSM/FEMA/3DEP | Demos run without user-written loaders |

## 8. Non-functional requirements
Transparency (no black-box scoring) · Reproducibility (same inputs → same scores) · Spatial
integrity (single metric CRS, valid geometry) · Portability (open-format export) · Small,
composable, well-typed surface over a thin geopandas core · Tested (pytest + fixture county) · CI.

---

## 9. Milestones
- **v0.1 — core is real:** Strategy/Result, the v0.1 filters + criteria, CRS handling, I/O,
  RV-storage notebook, tests. *Exit: `pip install propertiq`; RV notebook runs; scores reproduce a
  hand-checked overlay.*
- **v0.2 — ergonomics + draw:** YAML loader, `.explain()`, `.to_map()`, car-wash notebook,
  README demo GIF. *Exit: a stranger scores their own parcels in 10 lines from the quickstart.*
- **v0.3 — batteries:** `loaders/`, drive-time/isochrone scope + `Drivetime` criterion, docs site,
  `CONTRIBUTING` good-first-issues. *Exit: usable without writing loaders; open to contributors.*
- **Later (if traction):** raster criteria; AHP/pairwise weights; sensitivity analysis; a
  `propertiq.felt` adapter to push results into Felt — the bridge to a hosted product layer.

---

## 10. Repo hygiene for credibility
README that shows before it tells (demo GIF) · runnable example notebooks (Colab badge) · tests + CI
· typed (mypy) + linted (ruff) + pre-commit · LICENSE (MIT) · CONTRIBUTING + good-first-issues ·
CITATION.cff + Zenodo DOI on release · an opinionated, clearly-scoped README so it reads as a tool.

---

## 11. Differentiation
- **vs PyLUSAT / GDAL / QGIS:** they give suitability *primitives*; ProperTIQ gives a declarative,
  explainable, parcel-centric *workflow* with a real API and worked verticals.
- **vs Esri / SiteZeus / GrowthFactor:** they're paid, closed GUIs for retail chains; ProperTIQ is
  free, code-first, reproducible, BYO-data, verticals-agnostic.
- **vs leafmap / GeoLibre:** they're visualization/general analysis; ProperTIQ is the scoring/ranking
  layer and composes with them for the map.

---

## 12. First specs (for Spec Kit)
1. `spec: scoring-core` — Strategy/Filter/Criterion model + weighted scoring + breakdown (v0.1).
2. `spec: crs-handling` — reproject-to-metric, validate, warn.
3. `spec: yaml-strategies` — declarative loader + round-trip (v0.2).

`constitution.md` non-negotiables: explainable scoring (no black box) · BYO-data (never bundle/host
data) · metric CRS for all area/distance with validation · filters/criteria independently testable ·
results always export to open formats · small composable surface over a thin geopandas core.
