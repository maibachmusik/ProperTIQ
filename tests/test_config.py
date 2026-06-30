"""Config round-trip — SC-C1 (YAML ≡ Python), SC-C3 (clear errors)."""

from __future__ import annotations

import pytest

import propertiq as pq


def _rv_config():
    return {
        "name": "rv_storage",
        "filters": [
            {"min_area": {"acres": 3}},
            {
                "attr_in": {
                    "field": "zoning",
                    "values": ["industrial", "commercial", "agricultural"],
                }
            },
        ],
        "score": [
            {"proximity": {"to": "highways", "weight": 0.6, "prefer": "near"}},
            {"attr_value": {"field": "assessed_value", "weight": 0.4, "prefer": "low"}},
        ],
    }


def _python_strategy(highway):
    return pq.Strategy(
        name="rv_storage",
        filters=[
            pq.MinArea(acres=3),
            pq.AttrIn("zoning", ["industrial", "commercial", "agricultural"]),
        ],
        score=[
            pq.Proximity(to=highway, weight=0.6, prefer="near"),
            pq.AttrValue("assessed_value", weight=0.4, prefer="low"),
        ],
    )


def test_config_scores_match_python(parcels, highway):
    layers = {"highways": highway}
    from_cfg = pq.from_config(_rv_config(), layers=layers).run(parcels)
    from_py = _python_strategy(highway).run(parcels)
    assert from_cfg.parcels["score"].tolist() == pytest.approx(from_py.parcels["score"].tolist())
    assert from_cfg.parcels["pid"].tolist() == from_py.parcels["pid"].tolist()


def test_run_accepts_dict(parcels, highway):
    res = pq.run(_rv_config(), parcels, layers={"highways": highway})
    assert "score" in res.parcels.columns


def test_to_config_roundtrip(parcels, highway):
    layers = {"highways": highway}
    s = pq.from_config(_rv_config(), layers=layers)
    cfg = s.to_config(layer_names={id(highway): "highways"})
    assert cfg["name"] == "rv_storage"
    assert cfg["filters"][0] == {"min_area": {"acres": 3}}
    assert cfg["score"][0]["proximity"]["to"] == "highways"
    # rebuild from the dumped config → identical scores
    again = pq.from_config(cfg, layers=layers).run(parcels)
    base = s.run(parcels)
    assert again.parcels["score"].tolist() == pytest.approx(base.parcels["score"].tolist())


def test_yaml_file_roundtrip(parcels, highway, tmp_path):
    layers = {"highways": highway}
    s = pq.from_config(_rv_config(), layers=layers)
    path = tmp_path / "rv.yaml"
    pq.dump_strategy(s, str(path), layer_names={id(highway): "highways"})
    loaded = pq.load_strategy(str(path), layers=layers).run(parcels)
    base = s.run(parcels)
    assert loaded.parcels["score"].tolist() == pytest.approx(base.parcels["score"].tolist())


def test_unknown_block_key_raises():
    with pytest.raises(ValueError, match="unknown block"):
        pq.from_config(
            {"filters": [{"no_such_filter": {}}], "score": [{"attr_value": {"field": "x"}}]}
        )


def test_unknown_param_raises():
    with pytest.raises(ValueError, match="unknown param"):
        pq.from_config({"score": [{"attr_value": {"field": "x", "bogus": 1}}]})


def test_missing_layer_raises(parcels):
    with pytest.raises(KeyError, match="not a known layer"):
        pq.from_config({"score": [{"proximity": {"to": "ghost_layer"}}]}, layers={})


def test_unknown_top_level_key_raises():
    with pytest.raises(ValueError, match="unknown top-level"):
        pq.from_config({"filterz": []})


def test_missing_required_param_raises():
    with pytest.raises(ValueError, match="missing required"):
        pq.from_config({"score": [{"attr_value": {"prefer": "high"}}]})  # no field
