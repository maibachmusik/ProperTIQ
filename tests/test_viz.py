"""Result.to_map — SC-V1..V4."""

from __future__ import annotations

import pytest

import propertiq as pq

folium = pytest.importorskip("folium")


@pytest.fixture
def result(parcels, highway):
    return pq.Strategy(
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    ).run(parcels)


def test_to_map_returns_folium_map(result):
    m = result.to_map()
    assert isinstance(m, folium.Map)
    # at least one GeoJson layer was added
    assert any("GeoJson" in type(c).__name__ for c in m._children.values())


def test_to_map_on_non_score_column(result):
    m = result.to_map(column="assessed_value")
    assert isinstance(m, folium.Map)


def test_to_map_tooltip_carries_scores(result):
    html = result.to_map()._repr_html_()
    # SC-V4: a score value reached the rendered map (tooltip wired)
    assert any(str(round(s, 1)) in html for s in result.parcels["score"])


def test_to_map_unknown_column_raises(result):
    with pytest.raises(KeyError, match="nope"):
        result.to_map(column="nope")


def test_to_map_empty_result_raises(parcels, highway):
    empty = pq.Strategy(
        filters=[pq.AttrIn("zoning", ["does-not-exist"])],
        score=[pq.Proximity(to=highway)],
    ).run(parcels)
    with pytest.raises(ValueError, match="no candidates"):
        empty.to_map()


def test_to_map_top_n(result):
    m = result.to_map(n=2)
    assert isinstance(m, folium.Map)
