# Concepts

## Strategy = filters + criteria

A **`Strategy`** has two kinds of rules:

- **Hard filters** — pass/fail. A parcel must satisfy *all* of them to survive
  (e.g. "≥ 3 acres", "not in a floodplain"). Failing parcels are dropped.
- **Weighted scoring criteria** — soft signals combined into a 0–100 score
  (e.g. "closer to a highway is better, weight 0.30").

Both are small, independent, testable units. See the
[blocks reference](blocks.md) for the full catalog.

## The pipeline

`strategy.run(parcels)` executes, in order:

1. **Normalize CRS** — reproject parcels to the measurement CRS (default
   EPSG:5070) and repair geometry.
2. **Filter** — apply every filter; survivors continue.
3. **Score** — for each criterion, compute a raw per-parcel value, normalize it,
   and apply its `prefer` direction.
4. **Combine** — weight-normalize and sum into a 0–100 score.
5. **Rank** — sort by score (ties broken by original order, so runs are
   reproducible).

## The scoring math

Each criterion produces a raw value per parcel; the engine **min–max normalizes**
it across the candidate set:

```
norm(x) = (x - min) / (max - min)
```

- **Degenerate range** (all parcels equal, or only one survivor) → every parcel
  gets a neutral `0.5` (the criterion can't discriminate, so it neither rewards
  nor penalizes).
- **Missing values** → that parcel gets `0` for the criterion and is excluded from
  the min/max.
- **`prefer`** flips the signal so higher is always better: `near`/`low` →
  `1 - norm`; `far`/`high` → `norm`.

Weights auto-normalize (`w'ᵢ = wᵢ / Σw`), then:

```
score        = 100 · Σ (w'ᵢ · signalᵢ)
breakdown[i] = 100 ·  w'ᵢ · signalᵢ      # and Σ breakdown == score
```

That last identity is the no-black-box guarantee: every score is fully accounted
for by its parts.

!!! note "Why min–max over the candidate set?"
    Scores are relative to *the parcels you're actually deciding among* — your
    candidate set — not some external benchmark. That keeps the method
    data-free (you bring no reference layer) and the results interpretable.

## CRS handling

All area and distance math happens in one metric **measurement CRS** (default
**EPSG:5070**, CONUS Albers Equal Area):

- Inputs are reprojected and geometry is validated (`make_valid`).
- An input with **no CRS set is rejected** — an unknown CRS can't be measured
  safely.
- Layers you pass to filters/criteria (highways, floodplain, …) are reprojected
  to the measurement CRS and **warned about if they differed** — never silently
  joined across mismatched CRSs.

## Export

`result.to_file(path)` writes open formats:

- `.geojson` / `.json` → GeoJSON, reprojected to EPSG:4326 (the GeoJSON standard).
- `.parquet` → GeoParquet, keeping the measurement CRS.

The `score_breakdown` is serialized as a JSON string so it survives both formats.
