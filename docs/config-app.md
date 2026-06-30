# Config app (no-code)

A standalone app for building, running, and exporting a strategy **without writing
code** — for non-technical users and per-deployment configuration. It's a thin
client over the library: every block, label, and tooltip is read from
`propertiq.registry`, so the app's help text always matches what the engine does.

> The core library never depends on the app. It's a separate, optional deployable.

## Run it

```bash
pip install "propertiq[app]"
streamlit run app/strategy_builder.py
```

## What it does

1. **Upload data** — a parcels file plus any named layers (highways, competitors,
   floodplain…).
2. **Build a strategy** — add hard filters and scoring criteria from a labeled
   list. Each block and each input explains itself inline.
3. **Run** — see ranked candidates, a per-criterion "why" breakdown, and a map.
4. **Export** — download the scored candidates (GeoJSON) and the strategy (YAML).
   Re-load the YAML later to continue.

## It speaks the same YAML

The strategy the app exports is the exact format
[`pq.run(path, parcels, layers=...)`](yaml.md) consumes — build a strategy in the
app and run it in code, or vice-versa, with no translation.
