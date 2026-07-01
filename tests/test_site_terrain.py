"""Site & terrain blocks — SC-S1 (WithinDistance, CountRange, Facing, NearbyCount)."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

import propertiq as pq

CRS = "EPSG:5070"


def _ids(gdf):
    return set(gdf["pid"])


def test_within_distance(parcels, highway):
    # Distances to the x=0 highway: P0=0, P1=1000, P2=2000, P3=3000 m.
    from propertiq.crs import to_measurement_crs

    g = to_measurement_crs(parcels)
    survivors = pq.WithinDistance(highway, max_mi=1.0).apply(g, CRS)  # 1 mi = 1609 m
    assert _ids(survivors) == {"P0", "P1"}


def test_count_range_on_parcel(parcels, competitors):
    # Competitors intersect P0 (100,100) and P2 (2075,75); none on P1/P3.
    from propertiq.crs import to_measurement_crs

    g = to_measurement_crs(parcels)
    vacant = pq.CountRange(competitors, within_mi=0.0, max=0).apply(g, CRS)
    assert _ids(vacant) == {"P1", "P3"}
    occupied = pq.CountRange(competitors, within_mi=0.0, min=1).apply(g, CRS)
    assert _ids(occupied) == {"P0", "P2"}


def test_facing_with_wraparound():
    # aspect_deg near 0/360 must both count as North-facing.
    gdf = gpd.GeoDataFrame(
        {
            "pid": ["a", "b", "c", "d"],
            "aspect_deg": [10.0, 100.0, 190.0, 350.0],
            "geometry": [box(i, 0, i + 1, 1) for i in range(4)],
        },
        crs=CRS,
    )
    north = pq.Facing(direction="N", tolerance_deg=45).apply(gdf, CRS)
    assert set(north["pid"]) == {"a", "d"}  # 10° and 350° (wraparound)
    south = pq.Facing(direction="S", tolerance_deg=45).apply(gdf, CRS)
    assert set(south["pid"]) == {"c"}  # 190°


def test_facing_drops_missing_aspect():
    gdf = gpd.GeoDataFrame(
        {
            "pid": ["a", "b"],
            "aspect_deg": [5.0, float("nan")],
            "geometry": [box(0, 0, 1, 1), box(2, 0, 3, 1)],
        },
        crs=CRS,
    )
    out = pq.Facing(direction="N").apply(gdf, CRS)
    assert set(out["pid"]) == {"a"}


def test_nearby_count_prefers_density():
    parcels = gpd.GeoDataFrame(
        {
            "pid": ["A", "B", "C"],
            "geometry": [box(0, 0, 50, 50), box(1000, 0, 1050, 50), box(5000, 0, 5050, 50)],
        },
        crs=CRS,
    )
    pts = gpd.GeoDataFrame(
        {"geometry": [Point(25, 25), Point(60, 25), Point(25, 60), Point(1025, 25)]},
        crs=CRS,
    )  # 3 near A, 1 near B, 0 near C
    hi = pq.Strategy(score=[pq.NearbyCount(of=pts, within_mi=0.3, prefer="high")]).run(parcels)
    s_hi = dict(zip(hi.parcels["pid"], hi.parcels["score"]))
    assert s_hi["A"] > s_hi["B"] > s_hi["C"]
    lo = pq.Strategy(score=[pq.NearbyCount(of=pts, within_mi=0.3, prefer="low")]).run(parcels)
    s_lo = dict(zip(lo.parcels["pid"], lo.parcels["score"]))
    assert s_lo["C"] > s_lo["B"] > s_lo["A"]


def test_within_distance_empty_layer_raises(parcels):
    from propertiq.crs import to_measurement_crs

    g = to_measurement_crs(parcels)
    empty = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=CRS)
    with pytest.raises(ValueError, match="empty"):
        pq.WithinDistance(empty, max_mi=1.0).apply(g, CRS)
