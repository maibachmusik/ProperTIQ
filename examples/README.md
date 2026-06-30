# Examples

Worked notebooks running real, open data only. Each: load → declare strategy →
run → top-N map → `explain()` → export.

Install the demo deps with `pip install "propertiq[examples]"`.

- **`rv_storage.ipynb`** — RV/boat storage in Larimer County, CO. Pulls open
  parcels + zoning + FEMA floodplain (county/FEMA ArcGIS) and highways +
  competitors (OpenStreetMap via `osmnx`), then filters (zoning, size, avoid
  floodplain) and scores (highway proximity, competitor gap, acreage). Ends with a
  ranked map, a per-criterion `explain()` breakdown, and a GeoJSON + YAML export.
  The exported YAML is the same format the [config app](../app/README.md) uses.
- `car_wash_corridor.ipynb` — car-wash site finder along a metro corridor. *(coming in v0.2)*
