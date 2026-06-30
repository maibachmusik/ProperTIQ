# ProperTIQ — Strategy Builder (config app)

A standalone, no-code app for building, running, and exporting a ProperTIQ
scoring strategy. It is a thin client over the `propertiq` library: every filter,
criterion, and tooltip is read from `propertiq.registry`, so what you see always
matches what the engine does.

> The core `propertiq` library does **not** depend on this app. This is an
> optional, separately-installed deployable.

## Run it

```bash
pip install "propertiq[app]"
streamlit run app/strategy_builder.py
```

## What you can do

1. **Upload data** — a parcels file (GeoJSON or GeoParquet) and any number of
   named layers (highways, competitors, floodplain, …).
2. **Build a strategy** — add hard filters and weighted scoring criteria from a
   labeled list. Each block and each input explains itself inline (tooltips come
   from the library).
3. **Run** — see ranked candidates, a per-criterion "why" breakdown, and a map.
4. **Export** — download the scored candidates (GeoJSON) and the strategy itself
   (YAML). Re-load the YAML later to pick up where you left off.

## Notes

- Layer-typed inputs (e.g. *Proximity → Measure distance to*) and attribute
  inputs (*Allowed values → Parcel attribute*) populate from your uploaded data —
  no free-text guessing.
- The strategy YAML this app produces is the same format `propertiq.run(path,
  parcels, layers=...)` consumes, so a strategy built here runs unchanged in code.
- Logic is unit-tested in `tests/test_app_logic.py`; the UI module is import-safe
  (all rendering lives under `main()`).
