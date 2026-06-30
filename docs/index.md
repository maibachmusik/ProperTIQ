# ProperTIQ

**Site suitability as code.** Give ProperTIQ your parcels and a strategy — your
rules for what makes land good for a purpose — and get them back **scored 0–100,
ranked, with a transparent breakdown of why each scored what it did**.

```python
import propertiq as pq
import geopandas as gpd

parcels = gpd.read_file("parcels.geojson")

strategy = pq.Strategy(
    filters=[
        pq.MinArea(acres=3),
        pq.NotWithin(floodplain),
        pq.AttrIn("zoning", ["industrial", "commercial"]),
    ],
    score=[
        pq.Proximity(to=highways, weight=0.40, prefer="near"),
        pq.Gap(of=competitors, within_mi=5, weight=0.35),
        pq.AttrValue("acres", weight=0.25, prefer="high"),
    ],
)

result = strategy.run(parcels)
result.top(20)        # ranked candidates
result.explain()      # per-criterion contributions (they sum to the score)
result.to_map()       # interactive folium map
result.to_file("candidates.geojson")
```

## Why it's different

- **Explainable — no black box.** Every score decomposes into a per-criterion
  `score_breakdown` that sums to the score.
- **Bring your own data.** ProperTIQ owns the *method*, never the data. Nothing is
  bundled, hosted, or silently fetched — it scores whatever layers you bring.
- **Correct geometry.** All area/distance math runs in a single metric CRS, with
  geometry validation and mismatch warnings.
- **Two ways to drive it.** A small, typed Python API, or a declarative
  [YAML strategy](yaml.md) — and a no-code [config app](config-app.md) for
  non-technical users.

## Where to go next

- [Quickstart](quickstart.md) — install and run it.
- [Concepts](concepts.md) — the scoring model and CRS handling.
- [Blocks reference](blocks.md) — every filter and criterion.
- [Examples](examples.md) — worked notebooks on real open data.
