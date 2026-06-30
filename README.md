# ProperTIQ

**Site suitability as code — explainable, reproducible, bring-your-own-data.**

Declare a weighted site-selection strategy, run it over *your* parcels, and get ranked
candidates back with a transparent, per-criterion score breakdown.

> Status: **v0.1.** Scoring engine, declarative YAML strategies, interactive maps, a
> no-code config app, two worked notebooks on live open data, and docs are all in place.

---

## What it is

ProperTIQ is a small Python library that answers *"where should I put X?"* questions on land.
You give it (1) a set of parcels and (2) a **strategy** — hard filters plus weighted scoring
criteria — and it returns those parcels scored `0–100` and ranked, with an explanation of why
each scored what it did.

It owns the **method**, not the data. Bring parcels from any open county/state source; ProperTIQ
scores them. That's what keeps it free, reproducible, and verticals-agnostic.

## What it is not

- ❌ Not a hosted parcel-data service (bring your own data).
- ❌ Not skip-tracing, CRM, valuation/AVM, or sales forecasting.

The core library is GUI-free. A separate, optional [config app](app/README.md) provides a
no-code UI for people who'd rather not write Python.

## Install

```bash
pip install propertiq             # core: the scoring engine + maps
pip install "propertiq[app]"      # + the no-code config app (Streamlit)
pip install "propertiq[examples]" # + deps to run the example notebooks
pip install "propertiq[viz]"      # + leafmap (folium ships with core)
```

Python 3.10+.

## Quickstart

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
        pq.Proximity(to=highways,   weight=0.40, prefer="near"),
        pq.Gap(of=storage_pois,     within_mi=5, weight=0.35),   # competitor gap
        pq.AttrValue("acres",       weight=0.25, prefer="high"),
    ],
)

result = strategy.run(parcels)     # GeoDataFrame + score, rank, score_breakdown
result.top(20)                     # highest-scoring candidates
result.explain()                   # per-criterion contribution table (sums to the score)
result.to_map()                    # interactive folium map, colored by score
result.to_file("candidates.geojson")
```

## Strategy as code (YAML)

The same strategy as a version-controllable file — the format the config app reads and writes:

```yaml
# strategies/rv_storage.yaml
name: rv_storage
filters:
  - min_area:   {acres: 3}
  - not_within: {layer: fema_floodplain}
  - attr_in:    {field: zoning, values: [industrial, commercial, agricultural]}
score:
  - proximity:  {to: highways,     weight: 0.40, prefer: near}
  - gap:        {of: storage_pois, within_mi: 5, weight: 0.35}
  - attr_value: {field: acres,     weight: 0.25, prefer: high}
```

```python
result = pq.run("strategies/rv_storage.yaml", parcels, layers=layers)
```

## No-code config app

A standalone Strategy Builder for non-technical users:

```bash
pip install "propertiq[app]"
streamlit run app/strategy_builder.py
```

Pick a search area by **ZIP or address + radius**, bring your own parcels (with links to county/
state GIS portals) or use the built-in **Colorado Front Range demo** (real Larimer + Weld County
parcels), compose filters and weighted criteria from a labeled list — every option explained
inline — **tune the weights**, run, and export the candidates (GeoJSON) and the strategy (YAML).
See [`app/README.md`](app/README.md).

## Examples

Worked notebooks on live open data ([`examples/`](examples)):

- `rv_storage.ipynb` — RV/boat storage in Larimer County, CO.
- `car_wash.ipynb` — car-wash siting on traffic + competitor gap + demand.

## Why ProperTIQ

The weighted-overlay method is old; what's missing is a way to express it as **explainable,
reproducible, bring-your-own-data code**. Existing open tools are academic primitives; the
polished tools are paid, closed GUIs built for retail chains. ProperTIQ is the free, code-first,
verticals-agnostic middle.

## Docs

- Full docs (concepts, blocks reference, API): `mkdocs serve` (with `pip install "propertiq[docs]"`).
- [`docs/PRD.md`](docs/PRD.md) — full scope / product requirements.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add a filter or scoring criterion.

## License

[MIT](LICENSE). Cite via [`CITATION.cff`](CITATION.cff).
