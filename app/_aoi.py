"""Area-of-interest + data fetching for the config app (spec 003, rev 1.1).

App-only and network-touching: geocode a ZIP/address, build a circular AOI, and
fetch parcels + context layers for it. The core ``propertiq`` library never does
any of this — it stays bring-your-own-data (constitution 2). Demo parcels cover
the Colorado Front Range (Larimer County); everywhere else is bring-your-own.
"""

from __future__ import annotations

import io
import json
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

_MI_TO_M = 1609.344
_SQM_PER_ACRE = 4046.8564224
_SFHA = ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]

# Larimer County (CO Front Range demo) open endpoints.
_PARCELS = "https://maps1.larimer.org/arcgis/rest/services/MapServices/Parcels/MapServer/3"
_ZONING = "https://maps1.larimer.org/arcgis/rest/services/MapServices/LC_Zoning/MapServer/0"
_NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28"


# --------------------------------------------------------------------------- #
# Geocoding + AOI geometry
# --------------------------------------------------------------------------- #
def geocode_zip(zipcode: str) -> tuple[float, float, str]:
    """US ZIP → (lat, lon, 'Place, ST') via the offline pgeocode database."""
    import pgeocode

    rec = pgeocode.Nominatim("us").query_postal_code(str(zipcode).strip())
    if rec is None or rec.latitude != rec.latitude:  # NaN check
        raise ValueError(f"ZIP {zipcode!r} not found in the US ZIP database.")
    return float(rec.latitude), float(rec.longitude), f"{rec.place_name}, {rec.state_code}"


def geocode_address(query: str) -> tuple[float, float, str]:
    """Address/place → (lat, lon, query), biased to the US."""
    import osmnx as ox

    q = query.strip()
    if "usa" not in q.lower() and "united states" not in q.lower():
        q = f"{q}, USA"
    lat, lon = ox.geocode(q)
    return float(lat), float(lon), query.strip()


def aoi_from_point(lat: float, lon: float, radius_mi: float):
    """Return (circle_geom in EPSG:4326, bbox (w,s,e,n)) for a point + radius."""
    import geopandas as gpd
    from shapely.geometry import Point

    circle = (
        gpd.GeoSeries([Point(lon, lat)], crs=4326)
        .to_crs(5070)
        .buffer(radius_mi * _MI_TO_M)
        .to_crs(4326)
    )
    return circle.iloc[0], tuple(float(b) for b in circle.total_bounds)


# --------------------------------------------------------------------------- #
# Fetch helpers
# --------------------------------------------------------------------------- #
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ProperTIQ-app"})
    return urllib.request.urlopen(req, timeout=90).read()


def _esri(layer_url: str, bbox: tuple, fields: str) -> "Any":
    import geopandas as gpd

    w, s, e, n = bbox
    q = {
        "where": "1=1", "geometry": f"{w},{s},{e},{n}",
        "geometryType": "esriGeometryEnvelope", "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "outFields": fields,
        "outSR": "4326", "returnGeometry": "true", "f": "geojson",
    }
    gj = json.loads(_get(layer_url + "/query?" + urllib.parse.urlencode(q)))
    feats = gj.get("features", [])
    if not feats:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=4326)
    return gpd.GeoDataFrame.from_features(feats, crs=4326)


def fetch_front_range_parcels(bbox: tuple) -> "Any":
    """Real Larimer County parcels for the bbox, enriched with acres + zone.

    Returns an empty GeoDataFrame if the AOI is outside the demo coverage.
    """
    import geopandas as gpd

    parcels = _esri(_PARCELS, bbox, "PARCELNUM,LOCCITY")
    if len(parcels) == 0:
        return parcels
    parcels["acres"] = parcels.to_crs(5070).area / _SQM_PER_ACRE
    zoning = _esri(_ZONING, bbox, "ZONING_ABBRV_DISTRICT")
    if len(zoning):
        j = gpd.sjoin(
            parcels.to_crs(5070),
            zoning.to_crs(5070)[["ZONING_ABBRV_DISTRICT", "geometry"]],
            predicate="intersects", how="left",
        )
        j = j[~j.index.duplicated(keep="first")]
        parcels["zone"] = j["ZONING_ABBRV_DISTRICT"].reindex(parcels.index).values
    else:
        parcels["zone"] = None
    return parcels


def fetch_context(bbox: tuple) -> dict[str, Any]:
    """Context layers available anywhere in the US: highways (OSM) + floodplain (FEMA)."""
    import osmnx as ox

    layers: dict[str, Any] = {}
    try:
        roads = ox.features_from_bbox(
            tuple(bbox), tags={"highway": ["motorway", "trunk", "primary", "secondary"]}
        )
        roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])][["geometry"]]
        if len(roads):
            layers["highways"] = roads.reset_index(drop=True).to_crs(4326)
    except Exception:
        pass
    try:
        flood = _esri(_NFHL, bbox, "FLD_ZONE")
        if len(flood):
            sfha = flood[flood["FLD_ZONE"].isin(_SFHA)][["geometry"]].reset_index(drop=True)
            if len(sfha):
                layers["floodplain"] = sfha
    except Exception:
        pass
    return layers


def fetch_osm_points(bbox: tuple, tag_key: str, tag_value: str) -> "Any":
    """Fetch an OSM feature layer (e.g. amenity=car_wash, shop=storage_rental) as points."""
    import geopandas as gpd
    import osmnx as ox

    feats = ox.features_from_bbox(tuple(bbox), tags={tag_key: [tag_value]})
    if not len(feats):
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=4326)
    feats = feats[["geometry"]].reset_index(drop=True).to_crs(4326)
    return feats


def clip_to_aoi(gdf: "Any", circle) -> "Any":
    """Keep only features intersecting the AOI circle (both EPSG:4326)."""
    if gdf is None or len(gdf) == 0:
        return gdf
    return gdf[gdf.to_crs(4326).intersects(circle)].copy()


def read_upload(name: str, data: bytes) -> "Any":
    """Read an uploaded parcels file: GeoJSON, GeoParquet, or zipped Shapefile."""
    import geopandas as gpd

    lower = name.lower()
    if lower.endswith(".parquet"):
        return gpd.read_parquet(io.BytesIO(data))
    if lower.endswith(".zip"):
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(td)
            shp = next(Path(td).rglob("*.shp"), None)
            if shp is None:
                raise ValueError("zip has no .shp file; upload a zipped Shapefile.")
            return gpd.read_file(shp)
    return gpd.read_file(io.BytesIO(data))
