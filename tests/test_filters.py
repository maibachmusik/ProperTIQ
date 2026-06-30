"""Hard filters — SC-2."""

from __future__ import annotations

import pytest

import propertiq as pq
from propertiq.crs import to_measurement_crs

CRS = "EPSG:5070"


def _ids(gdf):
    return set(gdf["pid"])


def test_min_area_drops_small_parcels(parcels):
    g = to_measurement_crs(parcels)
    # ≥ 3 acres keeps P0(9.9), P2(5.6), P3(22.2); drops P1(2.47).
    survivors = pq.MinArea(acres=3).apply(g, CRS)
    assert _ids(survivors) == {"P0", "P2", "P3"}


def test_max_area_keeps_small(parcels):
    g = to_measurement_crs(parcels)
    survivors = pq.MaxArea(acres=6).apply(g, CRS)
    assert _ids(survivors) == {"P1", "P2"}  # 2.47 and 5.56 acres


def test_attr_in(parcels):
    g = to_measurement_crs(parcels)
    survivors = pq.AttrIn("zoning", ["industrial", "commercial"]).apply(g, CRS)
    assert _ids(survivors) == {"P0", "P2"}


def test_attr_range(parcels):
    g = to_measurement_crs(parcels)
    survivors = pq.AttrRange("assessed_value", min=150, max=350).apply(g, CRS)
    assert _ids(survivors) == {"P2", "P3"}  # 300 and 200


def test_not_within_floodplain(parcels, floodplain):
    g = to_measurement_crs(parcels)
    survivors = pq.NotWithin(floodplain).apply(g, CRS)
    assert _ids(survivors) == {"P0", "P1", "P2"}  # P3 dropped


def test_within_floodplain(parcels, floodplain):
    g = to_measurement_crs(parcels)
    survivors = pq.Within(floodplain).apply(g, CRS)
    assert _ids(survivors) == {"P3"}


def test_missing_field_raises(parcels):
    g = to_measurement_crs(parcels)
    with pytest.raises(KeyError, match="nope"):
        pq.AttrIn("nope", [1]).apply(g, CRS)
