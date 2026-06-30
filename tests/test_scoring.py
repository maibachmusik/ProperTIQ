"""Scoring engine — SC-1 (hand-computed), SC-3 (errors), SC-5 (ranking),
plus breakdown-sums, degenerate range, and NaN handling."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import box

import propertiq as pq

CRS = "EPSG:5070"


def _by_pid(result):
    return dict(zip(result.parcels["pid"], result.parcels["score"]))


def test_hand_computed_scores(parcels, highway):
    """SC-1: reproduce a fully hand-computed overlay.

    Proximity(near, w=0.6): distances [0,1000,2000,3000] → norm [0,1/3,2/3,1] →
        near-signal [1,2/3,1/3,0].
    AttrValue(low, w=0.4): assessed [400,100,300,200] → norm [1,0,2/3,1/3] →
        low-signal [0,1,1/3,2/3].
    score = 100*(0.6*prox + 0.4*attr).
    """
    strategy = pq.Strategy(
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    )
    scores = _by_pid(strategy.run(parcels))
    assert scores["P0"] == pytest.approx(60.0)
    assert scores["P1"] == pytest.approx(80.0)
    assert scores["P2"] == pytest.approx(100 / 3)
    assert scores["P3"] == pytest.approx(80 / 3)


def test_breakdown_sums_to_score(parcels, highway):
    result = pq.Strategy(
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    ).run(parcels)
    for _, row in result.parcels.iterrows():
        assert sum(row["score_breakdown"].values()) == pytest.approx(row["score"])


def test_breakdown_keys_dedupe_repeated_criteria(parcels, highway, competitors):
    result = pq.Strategy(
        score=[
            pq.Proximity(to=highway, weight=0.5, prefer="near"),
            pq.Proximity(to=competitors, weight=0.5, prefer="far"),
        ],
    ).run(parcels)
    keys = set(result.parcels["score_breakdown"].iloc[0].keys())
    assert keys == {"Proximity", "Proximity_2"}


def test_ranking_is_monotonic(parcels, highway):
    result = pq.Strategy(score=[pq.Proximity(to=highway, prefer="near")]).run(parcels)
    df = result.parcels
    assert list(df["rank"]) == sorted(df["rank"])
    assert list(df["score"]) == sorted(df["score"], reverse=True)
    # top(2) returns the two best by rank.
    assert list(result.top(2)["rank"]) == [1, 2]


def test_filters_then_score(parcels, highway):
    # MinArea(3) drops P1; remaining P0,P2,P3 are scored among themselves.
    result = pq.Strategy(
        filters=[pq.MinArea(acres=3)],
        score=[pq.Proximity(to=highway, prefer="near")],
    ).run(parcels)
    assert set(result.parcels["pid"]) == {"P0", "P2", "P3"}


def test_empty_score_raises(parcels):
    with pytest.raises(ValueError, match="at least one scoring criterion"):
        pq.Strategy(score=[]).run(parcels)


def test_zero_weights_raise(parcels, highway):
    with pytest.raises(ValueError, match="sum to zero"):
        pq.Strategy(
            score=[pq.Proximity(to=highway, weight=0.0)],
        ).run(parcels)


def test_negative_weight_raises(parcels, highway):
    with pytest.raises(ValueError, match="non-negative"):
        pq.Strategy(score=[pq.Proximity(to=highway, weight=-1.0)]).run(parcels)


def test_unknown_attr_field_raises(parcels):
    with pytest.raises(KeyError, match="ghost"):
        pq.Strategy(score=[pq.AttrValue("ghost")]).run(parcels)


def test_degenerate_single_survivor_scores_50(parcels, highway):
    # Filter down to one parcel → every criterion is degenerate → score 50.
    result = pq.Strategy(
        filters=[pq.AttrIn("pid", ["P0"])],
        score=[pq.Proximity(to=highway, prefer="near"), pq.AttrValue("assessed_value")],
    ).run(parcels)
    assert len(result.parcels) == 1
    assert float(result.parcels["score"].iloc[0]) == pytest.approx(50.0)


def test_nan_attribute_scores_zero():
    gdf = gpd.GeoDataFrame(
        {
            "pid": ["A", "B", "C", "D"],
            "val": [10.0, 20.0, float("nan"), 40.0],
            "geometry": [box(i, 0, i + 1, 1) for i in range(4)],
        },
        crs=CRS,
    )
    result = pq.Strategy(score=[pq.AttrValue("val", prefer="high")]).run(gdf)
    s = dict(zip(result.parcels["pid"], result.parcels["score"]))
    assert s["C"] == pytest.approx(0.0)  # NaN → worst
    assert s["D"] == pytest.approx(100.0)  # max


def test_gap_rewards_scarcity(parcels, competitors):
    # P3 has no competitors within range; P0 has two → P3 should outscore P0.
    result = pq.Strategy(score=[pq.Gap(of=competitors, within_mi=1.0)]).run(parcels)
    s = dict(zip(result.parcels["pid"], result.parcels["score"]))
    assert s["P3"] > s["P0"]


def test_empty_survivor_set_is_graceful(parcels, highway):
    result = pq.Strategy(
        filters=[pq.AttrIn("zoning", ["nonexistent"])],
        score=[pq.Proximity(to=highway)],
    ).run(parcels)
    assert len(result.parcels) == 0
    assert "score" in result.parcels.columns
    assert result.top(5).empty
