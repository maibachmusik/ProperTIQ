# Quickstart

## Install

```bash
pip install propertiq
```

Optional extras:

| Extra | Adds | For |
|---|---|---|
| `propertiq[viz]` | leafmap | richer maps (folium is already core) |
| `propertiq[app]` | streamlit | the [no-code config app](config-app.md) |
| `propertiq[examples]` | osmnx, mapclassify | running the [example notebooks](examples.md) |

ProperTIQ needs Python 3.10+ and builds on geopandas / shapely / pyproj.

## Score your parcels in ~10 lines

```python
import propertiq as pq
import geopandas as gpd

parcels = gpd.read_file("parcels.geojson")   # your land, with a CRS set
highways = gpd.read_file("highways.geojson")

strategy = pq.Strategy(
    filters=[pq.MinArea(acres=2)],                       # drop anything too small
    score=[pq.Proximity(to=highways, prefer="near")],    # reward closeness to a highway
)

result = strategy.run(parcels)
print(result.top(10)[["score", "rank"]])
```

## What you get back

`run()` returns a `Result` wrapping a `GeoDataFrame` of the surviving parcels with:

- `score` — 0–100, higher is better.
- `rank` — 1 = best.
- `score_breakdown` — a per-parcel `{criterion: contribution}` dict that **sums to
  the score**.
- a `signal__<criterion>` column per criterion (the normalized 0–1 signal).

And these methods:

- `result.top(n)` — the n best candidates.
- `result.explain()` — a contribution table (one column per criterion).
- `result.to_map()` — an interactive map colored by score.
- `result.to_file("out.geojson" | "out.parquet")` — open-format export.

!!! tip "Set a CRS"
    Inputs must have a CRS set (e.g. `gdf.set_crs("EPSG:4326")`). ProperTIQ
    reprojects everything to a metric measurement CRS (default EPSG:5070) for all
    area and distance math — an unknown CRS is rejected rather than guessed.
