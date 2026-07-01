"""App presets must stay valid against the registry / config layer."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString, box

import propertiq as pq
from app import _logic, presets


def _layers():
    return {
        "floodplain": gpd.GeoDataFrame({"geometry": [box(0, 0, 1, 1)]}, crs=4326),
        "highways": gpd.GeoDataFrame({"geometry": [LineString([(0, 0), (1, 1)])]}, crs=4326),
        "buildings": gpd.GeoDataFrame({"geometry": [box(0, 0, 1, 1)]}, crs=4326),
    }


@pytest.mark.parametrize("preset", presets.PRESETS, ids=[p["key"] for p in presets.PRESETS])
def test_preset_builds_a_strategy(preset):
    # Valid block keys/params and resolvable layer names → a real Strategy.
    strategy = pq.from_config(preset["config"], layers=_layers())
    assert isinstance(strategy, pq.Strategy)
    assert strategy.filters or strategy.score


@pytest.mark.parametrize("preset", presets.PRESETS, ids=[p["key"] for p in presets.PRESETS])
def test_preset_loads_into_builder_state(preset):
    state = _logic.config_to_session(preset["config"])
    assert state["name"] == preset["config"]["name"]
    assert len(state["filters"]) == len(preset["config"].get("filters", []))
    assert len(state["score"]) == len(preset["config"].get("score", []))


def test_preset_keys_and_needs():
    keys = [p["key"] for p in presets.PRESETS]
    assert len(keys) == len(set(keys))
    for p in presets.PRESETS:
        assert p["label"].strip() and p["desc"].strip()
        assert isinstance(p["needs"], list)
