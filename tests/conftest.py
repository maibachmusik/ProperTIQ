"""Fixture 'county': a tiny, deterministic, no-network parcel set built directly
in the measurement CRS (EPSG:5070, meters) so areas and distances are exact.

Four square parcels along the x-axis, plus a 'highway' line, competitor points,
and a floodplain polygon. Designed so one strategy can be hand-computed (see
test_scoring.py::test_hand_computed_scores).
"""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, box

CRS = "EPSG:5070"


@pytest.fixture
def parcels() -> gpd.GeoDataFrame:
    # (square, side) → area = side**2 m². acres = area / 4046.8564224
    geoms = [
        box(0, 0, 200, 200),  # P0: 40000 m²  = 9.884 ac, touches x=0
        box(1000, 0, 1100, 100),  # P1: 10000 m²  = 2.471 ac
        box(2000, 0, 2150, 150),  # P2: 22500 m²  = 5.559 ac
        box(3000, 0, 3300, 300),  # P3: 90000 m²  = 22.239 ac
    ]
    return gpd.GeoDataFrame(
        {
            "pid": ["P0", "P1", "P2", "P3"],
            "zoning": ["industrial", "residential", "commercial", "agricultural"],
            "assessed_value": [400, 100, 300, 200],
            "geometry": geoms,
        },
        crs=CRS,
    )


@pytest.fixture
def highway() -> gpd.GeoDataFrame:
    # Vertical line at x=0 → distances to parcels are 0, 1000, 2000, 3000 m.
    return gpd.GeoDataFrame({"geometry": [LineString([(0, -1000), (0, 2000)])]}, crs=CRS)


@pytest.fixture
def competitors() -> gpd.GeoDataFrame:
    # Two points clustered near P0, one near P2, none near P3.
    return gpd.GeoDataFrame(
        {"geometry": [Point(100, 100), Point(300, 300), Point(2075, 75)]}, crs=CRS
    )


@pytest.fixture
def floodplain() -> gpd.GeoDataFrame:
    # Covers P3 only.
    return gpd.GeoDataFrame({"geometry": [box(2900, -100, 3400, 400)]}, crs=CRS)
