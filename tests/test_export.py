"""Open-format export round-trip — SC-7."""

from __future__ import annotations

import json

import geopandas as gpd
import pytest

import propertiq as pq


@pytest.fixture
def result(parcels, highway):
    return pq.Strategy(
        name="rv_storage",
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    ).run(parcels)


def test_geoparquet_roundtrip_keeps_scores(result, tmp_path):
    path = tmp_path / "candidates.parquet"
    result.to_file(str(path))
    back = gpd.read_parquet(path)
    assert len(back) == len(result.parcels)
    assert list(back["rank"]) == list(result.parcels["rank"])
    assert back["score"].tolist() == pytest.approx(result.parcels["score"].tolist())
    # breakdown survives as JSON string that parses back and still sums to score.
    bd = json.loads(back.iloc[0]["score_breakdown"])
    assert sum(bd.values()) == pytest.approx(back.iloc[0]["score"])


def test_geojson_export_reprojects_to_4326(result, tmp_path):
    path = tmp_path / "candidates.geojson"
    result.to_file(str(path))
    back = gpd.read_file(path)
    assert str(back.crs).endswith("4326")
    assert len(back) == len(result.parcels)
    assert "score" in back.columns


def test_unknown_extension_raises(result, tmp_path):
    with pytest.raises(ValueError, match="unsupported export extension"):
        result.to_file(str(tmp_path / "candidates.shp"))


def test_explain_table_sums_to_score(result):
    table = result.explain()
    criteria_cols = [c for c in table.columns if c not in ("rank", "score")]
    assert table[criteria_cols].sum(axis=1).tolist() == pytest.approx(table["score"].tolist())
