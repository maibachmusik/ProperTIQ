"""Smoke tests for the public API surface (pre-engine)."""

import propertiq as pq


def test_imports_and_version():
    assert isinstance(pq.__version__, str)


def test_strategy_constructs():
    s = pq.Strategy(
        filters=[pq.MinArea(acres=3)],
        score=[pq.AttrValue("assessed_value", weight=1.0, prefer="low")],
        name="smoke",
    )
    assert s.name == "smoke"
    assert len(s.filters) == 1 and len(s.score) == 1
