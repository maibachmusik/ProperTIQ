# Spec 006 — Site & terrain rules (physical / topological features)

**Status:** ready to implement · **Milestone:** v0.3 · **Depends on:** specs 001, 002, 003.
**Constitution:** 1 (explainable), 2 (BYO data — core never fetches), 4 (independent blocks), 6.

## Summary
Add a family of rules about a parcel's **physical and topological character** —
terrain, structures, access, and land characteristics — plus a **category** on
every block so the config app and docs group them into sections (Size,
Attributes, Proximity & access, **Site & terrain**).

Most requested features reduce to a few reusable mechanics over data the user
brings (or the demo app fetches from open sources): **distance-to-a-layer**,
**count-features-nearby**, **direction a parcel faces**, and **terrain/attribute
values sampled onto parcels**. The core library stays bring-your-own-data; the
app enriches demo parcels (3DEP terrain, OSM structures) so the rules light up.

## Why
The owner wants ProperTIQ to feel like a real site-selection tool: filter and
score land on the physical realities that decide a site — how it faces, how
steep it is, what's built on and around it, whether it has road/utility/water
access, and land characteristics (zoning, soils, rights).

## The requested features → mechanic, data, status
| Requested | Rule / mechanic | Data (demo source) | Status |
|---|---|---|---|
| Cardinal direction facing | `Facing` filter (circular, on an `aspect_deg` column) | 3DEP DEM → aspect | **built** |
| Slope / steepness | `AttrRange`/`AttrValue` on a `slope_deg` column | 3DEP DEM → slope | **built** (via terrain enrichment + attribute blocks) |
| Structures on parcel | `CountRange` filter / `NearbyCount` on a buildings layer (radius 0) | OSM buildings | **built** |
| Neighboring structures | `NearbyCount` criterion / `CountRange` filter (radius > 0) | OSM buildings | **built** |
| Road access | `WithinDistance` filter (within X of roads) | OSM roads | **built** |
| Distance to utilities | `WithinDistance` / `Proximity` to a utilities layer | OSM `power=*` | **built** (proximity) |
| Water access / features | `WithinDistance` / `Proximity` to a water layer | OSM waterways / NHD | **built** (proximity) |
| Zoning | `AttrIn` on a `zone` column | county zoning | **built** (existing) |
| Vegetation / tree density | `NearbyCount` of tree features, or an attribute from a canopy layer | OSM `natural=tree*` / NLCD canopy | **partial** (vector now; raster canopy = next) |
| Soil / geology | `AttrIn`/`AttrRange`/`Index` on a soils layer joined to parcels | USDA SSURGO | **BYO / next** (bring the layer) |
| Water rights / ability | `AttrIn`/`AttrRange` on a rights attribute; or `WithinDistance` to a decree layer | CO DWR (administrative) | **BYO** (no clean open parcel attribute) |
| Mineral rights | `AttrIn` on an ownership/severed-estate attribute | title/ownership data | **BYO** (rarely open) |

> Honest note: water rights, mineral rights, and parcel-level soils are
> administrative/ownership datasets that aren't cleanly available as open parcel
> attributes. ProperTIQ supports them the moment you *bring* a layer/column that
> carries them — via the attribute and overlay blocks — but the demo won't
> fabricate them.

## New blocks (v0.3)
All operate on user-supplied layers/columns; none fetch data.

- **`WithinDistance(layer, max_mi)`** — *filter.* Keep parcels within `max_mi` of
  any feature in `layer` (road access, utility access, water access). Complements
  `Within`/`NotWithin`. Category: Proximity & access.
- **`NearbyCount(of, within_mi=1.0, weight=1.0, prefer="high")`** — *criterion.*
  Count features of `of` within `within_mi` of each parcel; score by count.
  `prefer="high"` rewards density (built-up / amenities), `"low"` rewards
  isolation. Generalizes `Gap` (which is `prefer="low"` for competitors).
  Category: Site & terrain.
- **`CountRange(of, within_mi=0.0, min=None, max=None)`** — *filter.* Keep parcels
  with a feature count in `[min, max]` within `within_mi`. `within_mi=0, max=0`
  ⇒ "no structures on the parcel" (vacant); `min=5` ⇒ "in a built-up area".
  Category: Site & terrain.
- **`Facing(field="aspect_deg", direction, tolerance_deg=45)`** — *filter.* Keep
  parcels whose mean aspect (degrees, 0=N, 90=E…) faces `direction`
  (`N/NE/E/SE/S/SW/W/NW`) within `±tolerance_deg`, handling circular wraparound
  (N spans 337.5–22.5). Category: Site & terrain.

Slope is covered by the existing `AttrRange`/`AttrValue` on a `slope_deg` column
(e.g. `AttrRange("slope_deg", max=15)` = buildable; `AttrValue("slope_deg",
prefer="low")` = flatter is better).

## Registry category (schema change)
`BlockSpec` gains a `category: str`. Every block (existing + new) is assigned one.
The app groups its "add a block" pickers by category; the generated docs blocks
page groups by category too. A drift test asserts every block has a non-empty
category.

## App: terrain + structures enrichment (demo only, `app/_enrich.py`)
For the Front-Range demo, after loading parcels the app enriches them with:
- `slope_deg`, `aspect_deg` — zonal mean over a 3DEP DEM fetched for the AOI
  (aspect via circular mean of sin/cos).
- `structures` — count of OSM building footprints intersecting each parcel.
…and registers `buildings`, `water`, `power` as named layers so the new blocks
have data. This lives in the app (network), not the core library.

## Functional requirements
| ID | Requirement | Acceptance |
|---|---|---|
| FR-S1 | `WithinDistance` keeps parcels within `max_mi` of a layer | Survivors match a manual distance check |
| FR-S2 | `NearbyCount` scores by feature count in radius; prefer high/low | Denser parcels score higher (or lower) as set |
| FR-S3 | `CountRange` filters by nearby feature count | `max=0, within_mi=0` drops parcels with any structure |
| FR-S4 | `Facing` keeps parcels facing a cardinal direction (circular) | A north-facing parcel passes `direction="N"`; wraparound works |
| FR-S5 | Every block has a `category`; app groups pickers by it | Registry drift + a rendered grouped picker |
| FR-S6 | Demo enrichment adds `slope_deg`/`aspect_deg`/`structures` + layers | A CO Front Range load yields those columns and layers |

## Success criteria
- **SC-S1:** On a fixture, `WithinDistance`, `NearbyCount`, `CountRange`, `Facing`
  each produce the hand-checked survivor/score set (incl. Facing wraparound).
- **SC-S2:** Registry drift + metadata: every block (incl. new) has a category,
  label, description, and per-param tooltips; new blocks appear in the app.
- **SC-S3 (live):** Loading a CO Front Range AOI yields real `slope_deg`,
  `aspect_deg`, and `structures`, and a `Facing`/structures strategy runs and maps.

## Assumptions
- Terrain enrichment uses USGS 3DEP (public ImageServer); structures use OSM.
- Aspect is a circular mean; parcels with flat/no-data terrain get NaN aspect
  (Facing drops them or they score neutral, per the engine's NaN rules).

## Open questions
- Raster canopy/NDVI (true vegetation density) and SSURGO soils are the next
  data integrations; deferred to keep this increment testable.
