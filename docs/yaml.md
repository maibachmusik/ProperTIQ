# Declarative strategies (YAML)

A strategy can live as data instead of code — the same rules, in a file anyone can
edit. This is what makes rules manipulable per deployment and what the
[config app](config-app.md) reads and writes.

## Format

```yaml
name: rv_storage
filters:
  - min_area:   {acres: 3}
  - not_within: {layer: fema_floodplain}
  - attr_in:    {field: zoning, values: [industrial, commercial, agricultural]}
score:
  - proximity: {to: highways,     weight: 0.30, prefer: near}
  - gap:       {of: storage_pois, within_mi: 5, weight: 0.25}
  - attr_value:{field: acres,     weight: 0.20, prefer: high}
```

- Each list item is a single-key mapping `{block_key: {params}}`. The keys are the
  block names in the [blocks reference](blocks.md).
- **Layer-typed params** (`layer`, `to`, `of`) hold the *name* of a layer; you
  supply the actual GeoDataFrames in a `layers` map at run time.

## Running a YAML strategy

```python
import propertiq as pq
import geopandas as gpd

parcels = gpd.read_file("parcels.geojson")
layers = {
    "highways": gpd.read_file("highways.geojson"),
    "storage_pois": gpd.read_file("competitors.geojson"),
    "fema_floodplain": gpd.read_file("flood.geojson"),
}

result = pq.run("rv_storage.yaml", parcels, layers=layers)
```

`pq.run` also accepts a config `dict` or a `Strategy` object.

## Round-trip

```python
strategy = pq.from_config(config_dict, layers=layers)   # dict  -> Strategy
config   = strategy.to_config(layer_names={...})         # Strategy -> dict
pq.dump_strategy(strategy, "strategy.yaml", layer_names={...})
loaded   = pq.load_strategy("strategy.yaml", layers=layers)
```

A YAML strategy and its Python equivalent produce identical scores — the YAML is
the same model, just serialized.
