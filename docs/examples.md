# Examples

Worked notebooks that run on real, open data only — load → declare a strategy →
run → ranked map → `explain()` → export. Install the demo deps with
`pip install "propertiq[examples]"`.

## RV / boat storage — Larimer County, CO

`examples/rv_storage.ipynb`

Pulls open parcels, zoning, and FEMA floodplain (county/FEMA ArcGIS) plus highways
and competitors (OpenStreetMap), derives acreage and zoning (the parcels carry
neither), then filters (commercial/industrial zoning, ≥ 0.5 acres, not in the
floodplain) and scores (highway proximity, competitor gap, acreage). Ends with a
ranked map, an `explain()` breakdown, and a GeoJSON + YAML export.

## Car wash — Larimer County, CO

`examples/car_wash.ipynb`

A high-traffic retail model: parcels + zoning, CDOT AADT traffic counts,
competitor car washes (OpenStreetMap), and optional ACS demand (median income /
vehicles per household). Scores on traffic exposure, competitor gap, and demand.

!!! note "Live data"
    The notebooks fetch from open endpoints at run time (nothing is bundled —
    that's the point). If a source is briefly unavailable the demo degrades rather
    than failing. The car-wash demand layer needs a free
    [Census API key](https://api.census.gov/data/key_signup.html); without one the
    notebook runs and simply skips that one criterion.
