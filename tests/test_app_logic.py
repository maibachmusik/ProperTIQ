"""Config-app logic — SC-A1..A4 (headless; no Streamlit runtime needed)."""

from __future__ import annotations

import importlib.util

import pytest

import propertiq as pq
from app import _logic
from propertiq import registry


def _rv_state():
    return {
        "name": "rv_storage",
        "filters": [
            {"key": "min_area", "params": {"acres": 3}},
            {
                "key": "attr_in",
                "params": {
                    "field": "zoning",
                    "values": ["industrial", "commercial", "agricultural"],
                },
            },
        ],
        "score": [
            {"key": "proximity", "params": {"to": "highways", "prefer": "near", "weight": 0.6}},
            {
                "key": "attr_value",
                "params": {"field": "assessed_value", "prefer": "low", "weight": 0.4},
            },
        ],
    }


def test_state_to_config_runs_and_matches_python(parcels, highway):
    config = _logic.session_to_config(_rv_state())
    from_app = pq.from_config(config, layers={"highways": highway}).run(parcels)
    from_py = pq.Strategy(
        filters=[
            pq.MinArea(acres=3),
            pq.AttrIn("zoning", ["industrial", "commercial", "agricultural"]),
        ],
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    ).run(parcels)
    assert from_app.parcels["score"].tolist() == pytest.approx(from_py.parcels["score"].tolist())


def test_every_param_widget_has_a_tooltip():
    for block in registry.REGISTRY:
        for p in block.params:
            spec = _logic.param_widget_spec(p, layer_names=["a", "b"], field_names=["x"])
            assert spec["help"].strip(), f"{block.key}.{p.name} widget missing tooltip"
            assert spec["label"].strip()


def test_layer_and_field_widgets_carry_options():
    prox = registry.get("proximity")
    to_param = next(p for p in prox.params if p.name == "to")
    spec = _logic.param_widget_spec(to_param, layer_names=["highways", "rivers"])
    assert spec["kind"] == "layer"
    assert spec["options"] == ["highways", "rivers"]

    attr = registry.get("attr_value")
    field_param = next(p for p in attr.params if p.name == "field")
    spec2 = _logic.param_widget_spec(field_param, field_names=["zoning", "assessed_value"])
    assert spec2["options"] == ["zoning", "assessed_value"]


def test_state_config_roundtrip():
    state = _rv_state()
    rt = _logic.config_to_session(_logic.session_to_config(state))
    # filters/score blocks preserve key + the params we set
    assert rt["name"] == state["name"]
    assert [b["key"] for b in rt["filters"]] == ["min_area", "attr_in"]
    assert rt["score"][0]["params"]["to"] == "highways"
    assert rt["score"][0]["params"]["weight"] == 0.6


def test_new_block_state_uses_registry_defaults():
    blk = _logic.new_block_state("proximity")
    assert blk["key"] == "proximity"
    assert blk["params"]["prefer"] == "near"  # registry default
    assert blk["params"]["weight"] == 1.0


def test_app_module_is_import_safe():
    # Importing the Streamlit app must not execute UI code (all under main()).
    if importlib.util.find_spec("streamlit") is None:
        pytest.skip("streamlit not installed")
    mod = importlib.import_module("app.strategy_builder")
    assert hasattr(mod, "main")
