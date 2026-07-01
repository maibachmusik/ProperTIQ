"""Terrain + structures enrichment for the config app (spec 006).

App-only and network-touching: fetch a 3DEP DEM and OSM features for the AOI, and
attach physical-site columns/layers to the parcels so the Site & terrain blocks
(Facing, slope, structures, access) have data. The core library never fetches.
"""

from __future__ import annotations

import urllib.request
from typing import Any

_SQM = 4046.8564224
_3DEP = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
)
# OSM site layers to offer for proximity / density / access rules.
_OSM_LAYERS = {
    "buildings": {"building": True},
    "water": {"waterway": True, "natural": ["water"]},
    "power": {"power": ["line", "substation", "tower", "minor_line"]},
    "roads": {"highway": ["motorway", "trunk", "primary", "secondary", "tertiary"]},
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ProperTIQ-app"})
    return urllib.request.urlopen(req, timeout=90).read()


def fetch_site_layers(bbox: tuple) -> dict[str, Any]:
    """OSM structures / water / power / roads for the AOI, as named layers."""
    import osmnx as ox

    layers: dict[str, Any] = {}
    for name, tags in _OSM_LAYERS.items():
        try:
            g = ox.features_from_bbox(tuple(bbox), tags=tags)
            if name in ("roads",):
                g = g[g.geometry.type.isin(["LineString", "MultiLineString"])]
            g = g[["geometry"]].reset_index(drop=True).to_crs(4326)
            if len(g):
                layers[name] = g
        except Exception:
            continue
    return layers


def count_intersecting(parcels: "Any", layer: "Any") -> "Any":
    import geopandas as gpd
    import pandas as pd

    joined = gpd.sjoin(
        parcels[[parcels.geometry.name]],
        layer[[layer.geometry.name]],
        predicate="intersects",
        how="left",
    )
    counts = joined.groupby(joined.index)["index_right"].count()
    return pd.Series(counts, index=parcels.index).fillna(0).astype(int)


def _terrain(parcels: "Any", max_px: int = 900):
    """Return (slope_deg, aspect_deg) per parcel, sampled from a 3DEP DEM.

    Uses fast per-centroid sampling (vectorized) rather than full polygon zonal
    stats — parcel-level terrain, quick enough for an interactive load.
    """
    import numpy as np
    from rasterio.io import MemoryFile

    p = parcels.to_crs(5070)
    w, s, e, n = (float(b) for b in p.total_bounds)
    res = max(10.0, max(e - w, n - s) / max_px)
    W, H = max(1, int((e - w) / res)), max(1, int((n - s) / res))
    url = (
        f"{_3DEP}?bbox={w},{s},{e},{n}&bboxSR=5070&imageSR=5070&size={W},{H}"
        "&format=tiff&pixelType=F32&interpolation=RSP_BilinearInterpolation&f=image"
    )
    with MemoryFile(_get(url)) as mf, mf.open() as ds:
        dem = ds.read(1).astype("float64")
        transform = ds.transform
        nodata = ds.nodata
    if nodata is not None:
        dem[dem == nodata] = np.nan
    px, py = abs(transform.a), abs(transform.e)
    dzdy, dzdx = np.gradient(dem, py, px)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    aspect = np.degrees(np.arctan2(dzdy, -dzdx)) % 360.0

    # Sample each parcel centroid's pixel (vectorized inverse transform).
    cent = p.geometry.representative_point()
    inv = ~transform
    cols, rows = inv * (cent.x.to_numpy(), cent.y.to_numpy())
    rows = np.clip(np.asarray(rows, dtype=int), 0, dem.shape[0] - 1)
    cols = np.clip(np.asarray(cols, dtype=int), 0, dem.shape[1] - 1)
    return slope[rows, cols], aspect[rows, cols]


def add_terrain(parcels: "Any") -> "Any":
    """Attach slope_deg + aspect_deg from a 3DEP DEM (fast; ~1s). Returns a copy."""
    out = parcels.copy()
    slope_deg, aspect_deg = _terrain(out)
    out["slope_deg"] = slope_deg
    out["aspect_deg"] = aspect_deg
    return out


def add_structures(parcels: "Any", buildings: "Any") -> "Any":
    """Attach a `structures` count (OSM buildings intersecting each parcel)."""
    out = parcels.copy()
    out["structures"] = count_intersecting(out, buildings)
    return out


def enrich(parcels: "Any", bbox: tuple) -> tuple["Any", dict[str, Any]]:
    """Full enrichment (terrain + structures + site layers) — used by notebooks/tests.

    The app splits these (fast terrain on load; slower OSM layers on demand).
    """
    layers = fetch_site_layers(bbox)
    out = add_terrain(parcels)
    if "buildings" in layers:
        out = add_structures(out, layers["buildings"])
    return out, layers
