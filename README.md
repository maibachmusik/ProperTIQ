# ProperTIQ

**Site suitability as code — explainable, reproducible, bring-your-own-data.**

Declare a weighted site-selection strategy, run it over *your* parcels, and get ranked
candidates back with a transparent, per-criterion score breakdown.

> Status: **alpha / pre-release.** The API below is the design target (see [`docs/PRD.md`](docs/PRD.md)).
> Core scoring engine is being built toward `v0.1`.

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
- ❌ Not a web app or GUI.
- ❌ Not skip-tracing, CRM, valuation/AVM, or sales forecasting.

## Install

```bash
pip install propertiq          # core
pip install "propertiq[viz]"   # + interactive maps (leafmap)
```

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
        pq.Proximity(to=highways,     weight=0.30, prefer="near"),
        pq.Gap(of=storage_pois,       within_mi=5, weight=0.25),   # competitor gap
        pq.Index(acs_demand_index,    weight=0.25),
        pq.Proximity(to=rv_dealers,   weight=0.20, prefer="near"),
    ],
)

result = strategy.run(parcels)     # GeoDataFrame + score, rank, score_breakdown
result.top(20)                     # highest-scoring candidates
result.explain()                   # per-criterion contribution table
result.to_map()                    # interactive map (needs [viz])
result.to_file("candidates.geojson")
```

## Strategy as code

The same strategy as a version-controllable YAML file:

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

```python
result = pq.run("strategies/rv_storage.yaml", parcels, layers=layers)
```

## Why ProperTIQ

The weighted-overlay method is old; what's missing is a way to express it as **explainable,
reproducible, bring-your-own-data code**. Existing open tools are academic primitives; the
polished tools are paid, closed GUIs built for retail chains. ProperTIQ is the free, code-first,
verticals-agnostic middle.

## Docs

- [`docs/PRD.md`](docs/PRD.md) — full scope / product requirements.
- [`examples/`](examples) — worked notebooks (RV/boat storage, car wash).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add a filter or scoring criterion.

## License

[MIT](LICENSE). Cite via [`CITATION.cff`](CITATION.cff).
