"""Terrain + structures + land-characteristics enrichment for the config app (spec 006).

App-only and network-touching: fetch open datasets for the AOI (3DEP terrain,
LANDFIRE canopy, USDA SSURGO soils, OSM features) and attach physical-site
columns/layers so the Site & terrain rules have data. The core library never fetches.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

_SQM = 4046.8564224
_3DEP = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
)
_CANOPY = (
    "https://lfps.usgs.gov/arcgis/rest/services/Landfire_LF2024/"
    "LF2024_CC_CONUS/ImageServer/exportImage"
)
_SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
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


def _fetch_raster(parcels_5070: "Any", base_url: str, extra: str = "", res_floor: float = 30.0):
    """Fetch a GeoTIFF for the parcels' extent (EPSG:5070) → (array, transform, nodata)."""
    from rasterio.io import MemoryFile

    w, s, e, n = (float(b) for b in parcels_5070.total_bounds)
    res = max(res_floor, max(e - w, n - s) / 900)
    ww, hh = max(1, int((e - w) / res)), max(1, int((n - s) / res))
    url = (
        f"{base_url}?bbox={w},{s},{e},{n}&bboxSR=5070&imageSR=5070&size={ww},{hh}"
        f"&format=tiff{extra}&f=image"
    )
    with MemoryFile(_get(url)) as mf, mf.open() as ds:
        return ds.read(1).astype("float64"), ds.transform, ds.nodata


def _centroid_pixels(parcels_5070: "Any", transform, shape):
    """Row/col pixel indices for each parcel's representative point (vectorized)."""
    import numpy as np

    cent = parcels_5070.geometry.representative_point()
    cols, rows = (~transform) * (cent.x.to_numpy(), cent.y.to_numpy())
    rows = np.clip(np.asarray(rows, dtype=int), 0, shape[0] - 1)
    cols = np.clip(np.asarray(cols, dtype=int), 0, shape[1] - 1)
    return rows, cols


def _terrain(parcels: "Any"):
    """Return (slope_deg, aspect_deg) per parcel, sampled from a 3DEP DEM."""
    import numpy as np

    p = parcels.to_crs(5070)
    dem, transform, nodata = _fetch_raster(
        p, _3DEP, extra="&pixelType=F32&interpolation=RSP_BilinearInterpolation", res_floor=10.0
    )
    if nodata is not None:
        dem[dem == nodata] = np.nan
    px, py = abs(transform.a), abs(transform.e)
    dzdy, dzdx = np.gradient(dem, py, px)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    aspect = np.degrees(np.arctan2(dzdy, -dzdx)) % 360.0
    rows, cols = _centroid_pixels(p, transform, dem.shape)
    return slope[rows, cols], aspect[rows, cols]


def add_canopy(parcels: "Any") -> "Any":
    """Attach `canopy_pct` (0–100) from LANDFIRE forest canopy cover (NoData → 0)."""

    p = parcels.to_crs(5070)
    arr, transform, nodata = _fetch_raster(p, _CANOPY)
    if nodata is not None:
        arr[arr == nodata] = 0.0
    arr[arr < 0] = 0.0
    rows, cols = _centroid_pixels(p, transform, arr.shape)
    out = parcels.copy()
    out["canopy_pct"] = arr[rows, cols]
    return out


def fetch_soils(bbox: tuple) -> "Any":
    """USDA SSURGO map units for the AOI (polygons + drainage/hydric/farmland attrs)."""
    import geopandas as gpd
    from shapely import wkt

    w, s, e, n = bbox
    aoi = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
    sql = (
        "SELECT P.mukey, mu.muname, mu.farmlndcl, m.drclassdcd, m.hydgrpdcd, "
        "m.hydclprs, m.flodfreqdcd, P.mupolygongeo.STAsText() AS wkt "
        "FROM mupolygon P JOIN mapunit mu ON mu.mukey=P.mukey "
        "JOIN muaggatt m ON m.mukey=P.mukey "
        f"WHERE P.mupolygongeo.STIntersects(geometry::STGeomFromText('{aoi}',4326))=1"
    )
    req = urllib.request.Request(
        _SDA,
        data=json.dumps({"format": "JSON+COLUMNNAME", "query": sql}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "ProperTIQ-app"},
    )
    tbl = json.loads(urllib.request.urlopen(req, timeout=120).read()).get("Table", [])
    if len(tbl) < 2:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=4326)
    recs = [dict(zip(tbl[0], row)) for row in tbl[1:]]
    return gpd.GeoDataFrame(recs, geometry=[wkt.loads(r["wkt"]) for r in recs], crs=4326).drop(
        columns="wkt"
    )


def add_soils(parcels: "Any", soils: "Any") -> "Any":
    """Attach dominant soil columns (soil_drainage, soil_hydric_pct, soil_hydro_group)."""
    import geopandas as gpd
    import pandas as pd

    out = parcels.copy()
    if soils is None or len(soils) == 0:
        return out
    pts = out.copy()
    pts[pts.geometry.name] = out.geometry.representative_point()
    joined = gpd.sjoin(pts.to_crs(4326), soils.to_crs(4326), predicate="within", how="left")
    joined = joined[~joined.index.duplicated(keep="first")]
    out["soil_drainage"] = joined["drclassdcd"].reindex(out.index).values
    out["soil_hydro_group"] = joined["hydgrpdcd"].reindex(out.index).values
    out["soil_hydric_pct"] = pd.to_numeric(
        joined["hydclprs"].reindex(out.index), errors="coerce"
    ).values
    return out


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


def add_land(parcels: "Any", bbox: tuple) -> tuple["Any", dict[str, Any]]:
    """Attach canopy + soil columns and return the soils polygons as a layer.

    Fast (canopy raster ~0.5s, SSURGO SDA ~2s). Each step is best-effort.
    """
    out = parcels
    layers: dict[str, Any] = {}
    try:
        out = add_canopy(out)
    except Exception:
        pass
    try:
        soils = fetch_soils(bbox)
        if len(soils):
            out = add_soils(out, soils)
            layers["soils"] = soils
    except Exception:
        pass
    return out, layers


def enrich(parcels: "Any", bbox: tuple) -> tuple["Any", dict[str, Any]]:
    """Full enrichment (terrain + land + structures + site layers) — notebooks/tests.

    The app splits these (fast terrain/land on load; slower OSM layers on demand).
    """
    layers = fetch_site_layers(bbox)
    out = add_terrain(parcels)
    out, land_layers = add_land(out, bbox)
    layers.update(land_layers)
    if "buildings" in layers:
        out = add_structures(out, layers["buildings"])
    return out, layers
