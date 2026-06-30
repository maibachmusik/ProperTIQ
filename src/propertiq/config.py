"""Build a :class:`Strategy` from a plain config (dict or YAML) and serialize one
back, using the :mod:`registry` as the schema.

Config shape (canonical)::

    {
      "name": "rv_storage",
      "filters": [{"min_area": {"acres": 3}}, ...],
      "score":   [{"proximity": {"to": "highways", "weight": 0.3, "prefer": "near"}}, ...],
    }

``layer``-typed params hold the *name* of a user-supplied GeoDataFrame; pass a
``layers`` map (``{name: GeoDataFrame}``) so they resolve. Implements ``spec 002``.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from . import registry
from .strategy import Criterion, Filter, Strategy

if TYPE_CHECKING:
    pass


def _is_geodataframe(obj: Any) -> bool:
    return type(obj).__name__ in ("GeoDataFrame", "GeoSeries")


def _resolve_layer(
    value: Any, layers: dict[str, Any] | None, key: str, param: str, allow_column: bool
) -> Any:
    """Resolve a ``layer``-typed param value (a name) to a GeoDataFrame.

    ``allow_column`` (Index only) lets a bare string pass through as a parcel
    column name instead of requiring a layer.
    """
    if _is_geodataframe(value):
        return value
    layers = layers or {}
    if value in layers:
        return layers[value]
    if allow_column and isinstance(value, str):
        return value  # Index treats an unknown string as a parcel column name
    raise KeyError(
        f"{key}.{param}={value!r} is not a known layer; "
        f"pass it in layers= (available: {sorted(layers)})."
    )


def _build_block(item: dict[str, Any], layers: dict[str, Any] | None, kind: str) -> Any:
    if not isinstance(item, dict) or len(item) != 1:
        raise ValueError(
            f"each {kind} entry must be a single-key mapping like "
            f"{{'min_area': {{'acres': 3}}}}; got {item!r}."
        )
    ((block_key, params),) = item.items()
    spec = registry.get(block_key)
    if spec.kind != kind:
        raise ValueError(f"{block_key!r} is a {spec.kind}, not a {kind}.")
    params = dict(params or {})
    valid = {p.name for p in spec.params}
    unknown = set(params) - valid
    if unknown:
        raise ValueError(
            f"{block_key!r} got unknown param(s) {sorted(unknown)}; valid: {sorted(valid)}."
        )
    kwargs: dict[str, Any] = {}
    for p in spec.params:
        if p.name not in params:
            if p.required:
                raise ValueError(f"{block_key!r} is missing required param {p.name!r}.")
            continue
        val = params[p.name]
        if p.type == "layer":
            val = _resolve_layer(
                val, layers, block_key, p.name, allow_column=(block_key == "index")
            )
        kwargs[p.name] = val
    return spec.cls(**kwargs)


def from_config(config: dict[str, Any], layers: dict[str, Any] | None = None) -> Strategy:
    """Build a :class:`Strategy` from a config dict (see module docstring)."""
    if not isinstance(config, dict):
        raise ValueError(f"config must be a mapping; got {type(config).__name__}.")
    unknown = set(config) - {"name", "filters", "score"}
    if unknown:
        raise ValueError(f"unknown top-level config key(s) {sorted(unknown)}.")
    flist = [_build_block(it, layers, "filter") for it in config.get("filters", [])]
    slist = [_build_block(it, layers, "criterion") for it in config.get("score", [])]
    return Strategy(filters=flist, score=slist, name=config.get("name"))


def to_config(strategy: Strategy, layer_names: dict[int, str] | None = None) -> dict[str, Any]:
    """Serialize a :class:`Strategy` back to a config dict.

    ``layer_names`` maps ``id(geodataframe) -> name`` so ``layer`` params emit
    their name. Without it, GeoDataFrame-valued params emit a ``"<layer>"``
    placeholder and warn — the app serializes from its form instead (spec 003).
    """
    layer_names = layer_names or {}

    def emit(block: Filter | Criterion) -> dict[str, Any]:
        spec = registry.for_class(type(block))
        params: dict[str, Any] = {}
        for p in spec.params:
            val = getattr(block, p.name, None)
            if val is None and not p.required:
                continue
            if p.type == "layer" and _is_geodataframe(val):
                name = layer_names.get(id(val))
                if name is None:
                    warnings.warn(
                        f"no name known for the layer in {spec.key}.{p.name}; "
                        "emitting placeholder. Provide layer_names= for a faithful dump.",
                        stacklevel=2,
                    )
                    name = "<layer>"
                val = name
            elif isinstance(val, tuple):
                val = list(val)
            params[p.name] = val
        return {spec.key: params}

    return {
        "name": strategy.name,
        "filters": [emit(f) for f in strategy.filters],
        "score": [emit(c) for c in strategy.score],
    }
