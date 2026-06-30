"""CRS normalization and alignment — SC-4, SC-6."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import box

from propertiq.crs import ensure_aligned, to_measurement_crs

_ACRE_M2 = 4046.8564224


def test_area_in_metric_crs_is_correct(parcels):
    # SC-4: P3 is a 300m square = 90000 m² = 22.2388 acres (±0.1%).
    out = to_measurement_crs(parcels)
    p3 = out[out["pid"] == "P3"]
    acres = float(p3.geometry.area.iloc[0]) / _ACRE_M2
    assert acres == pytest.approx(90000 / _ACRE_M2, rel=1e-3)


def test_reprojects_wgs84_input():
    # SC-6: a WGS84 box reprojects to 5070 and gains a sensible positive area.
    gdf = gpd.GeoDataFrame({"geometry": [box(-105.1, 40.5, -105.0, 40.6)]}, crs="EPSG:4326")
    out = to_measurement_crs(gdf)
    assert str(out.crs).endswith("5070")
    assert float(out.geometry.area.iloc[0]) > 0


def test_missing_crs_raises():
    gdf = gpd.GeoDataFrame({"geometry": [box(0, 0, 1, 1)]})  # no crs
    with pytest.raises(ValueError, match="no CRS"):
        to_measurement_crs(gdf)


def test_ensure_aligned_warns_on_mismatch():
    gdf = gpd.GeoDataFrame({"geometry": [box(-105, 40, -104, 41)]}, crs="EPSG:4326")
    with pytest.warns(UserWarning, match="reprojecting"):
        (aligned,) = ensure_aligned(gdf, crs="EPSG:5070")
    assert str(aligned.crs).endswith("5070")


def test_ensure_aligned_no_warning_when_matching(parcels, recwarn):
    ensure_aligned(parcels, crs="EPSG:5070")
    assert not recwarn.list
