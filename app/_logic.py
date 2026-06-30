"""Pure, Streamlit-free logic for the config app: convert the builder's session
state to/from a ProperTIQ config, and resolve registry params to widget specs.

Kept separate from the UI so it is unit-tested headlessly (no Streamlit runtime).
Implements ``spec 003`` (FR-A2..A5, A8). Every block label/tooltip is sourced
from :mod:`propertiq.registry`, never hard-coded here.
"""

from __future__ import annotations

from typing import Any

from propertiq import registry

# --- Session-state model -----------------------------------------------------
# state = {
#   "name": str,
#   "filters": [{"key": "min_area", "params": {"acres": 3}}, ...],
#   "score":   [{"key": "proximity", "params": {"to": "highways", ...}}, ...],
# }


def new_state(name: str = "my_strategy") -> dict[str, Any]:
    """An empty builder state."""
    return {"name": name, "filters": [], "score": []}


def new_block_state(block_key: str) -> dict[str, Any]:
    """A new block entry pre-filled with the registry defaults for its params."""
    spec = registry.get(block_key)
    params = {p.name: _default_for(p) for p in spec.params}
    return {"key": block_key, "params": params}


def _default_for(param: registry.ParamSpec) -> Any:
    if param.default is not None:
        return list(param.default) if isinstance(param.default, tuple) else param.default
    if param.type == "multiselect":
        return []
    return None


def param_widget_spec(
    param: registry.ParamSpec,
    *,
    layer_names: list[str] | None = None,
    field_names: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve a :class:`ParamSpec` into a concrete widget descriptor for the UI.

    The ``help`` tooltip is always carried through verbatim from the registry, so
    the UI cannot show copy that disagrees with the engine.
    """
    options: list[Any] | None = None
    if param.type == "layer":
        options = list(layer_names or [])
    elif param.type == "field":
        options = list(field_names or [])
    elif param.type in ("select", "multiselect") and param.options:
        options = list(param.options)
    return {
        "name": param.name,
        "kind": param.type,
        "label": param.label,
        "help": param.help,
        "default": _default_for(param),
        "options": options,
        "min": param.min,
        "max": param.max,
        "required": param.required,
    }


# --- State <-> config --------------------------------------------------------
def session_to_config(state: dict[str, Any]) -> dict[str, Any]:
    """Reshape the builder state into a canonical ProperTIQ config dict.

    Unset optional params (``None`` / empty) are dropped so the config stays clean.
    """

    def emit(block: dict[str, Any]) -> dict[str, Any]:
        spec = registry.get(block["key"])
        required = {p.name for p in spec.params if p.required}
        params = {
            name: value
            for name, value in block.get("params", {}).items()
            if name in required or _is_set(value)
        }
        return {block["key"]: params}

    return {
        "name": state.get("name"),
        "filters": [emit(b) for b in state.get("filters", [])],
        "score": [emit(b) for b in state.get("score", [])],
    }


def config_to_session(config: dict[str, Any]) -> dict[str, Any]:
    """Inverse of :func:`session_to_config` — load a config back into builder state."""

    def to_block(item: dict[str, Any]) -> dict[str, Any]:
        ((key, params),) = item.items()
        spec = registry.get(key)  # validates the key
        full = {p.name: _default_for(p) for p in spec.params}
        full.update(params or {})
        return {"key": key, "params": full}

    return {
        "name": config.get("name"),
        "filters": [to_block(it) for it in config.get("filters", [])],
        "score": [to_block(it) for it in config.get("score", [])],
    }


def _is_set(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, str)) and len(value) == 0:
        return False
    return True
