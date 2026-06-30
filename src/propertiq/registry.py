"""The block registry: one declarative catalog of every filter and scoring
criterion, with human-facing metadata (label, plain-language description, and
per-parameter tooltips).

This is the single source of truth shared by the engine, the YAML config layer
(``config.py``), and the standalone config app (spec 003). Because the app builds
its forms and tooltips from here, **the help text can never drift from behavior**.

Implements ``spec 002``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import filters as _f
from . import scoring as _s

# Parameter widget/value types the config app understands.
#   number | integer | text | bool | select | multiselect | layer | field
#   - "layer": value is the NAME of a user-supplied GeoDataFrame (resolved via a
#     layers map at build time).
#   - "field": value is the name of a column on the parcels.
ParamType = str


@dataclass(frozen=True)
class ParamSpec:
    """One configurable parameter of a block, plus the copy a UI needs to explain it."""

    name: str
    type: ParamType
    label: str
    help: str  # tooltip — must be non-empty, plain language
    default: Any = None
    options: tuple[Any, ...] | None = None  # for select / multiselect
    min: float | None = None
    max: float | None = None
    required: bool = True


@dataclass(frozen=True)
class BlockSpec:
    """A filter or criterion: its YAML key, its class, and how to describe/configure it."""

    key: str
    kind: str  # "filter" | "criterion"
    cls: type
    label: str
    description: str  # plain-language: what this rule does
    params: tuple[ParamSpec, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- #
# The catalog. Keys match the declarative YAML names in PRD §4.
# --------------------------------------------------------------------------- #
_PREFER_HL = ("high", "low")
_PREFER_NF = ("near", "far")

REGISTRY: tuple[BlockSpec, ...] = (
    # ---- Filters (hard pass/fail) ---------------------------------------- #
    BlockSpec(
        key="min_area",
        kind="filter",
        cls=_f.MinArea,
        label="Minimum area",
        description="Keep only parcels at least this many acres. Drops anything too small.",
        params=(
            ParamSpec(
                "acres",
                "number",
                "Minimum acres",
                "Parcels smaller than this many acres are removed.",
                default=1.0,
                min=0,
            ),
        ),
    ),
    BlockSpec(
        key="max_area",
        kind="filter",
        cls=_f.MaxArea,
        label="Maximum area",
        description="Keep only parcels no larger than this many acres. Drops anything too big.",
        params=(
            ParamSpec(
                "acres",
                "number",
                "Maximum acres",
                "Parcels larger than this many acres are removed.",
                default=100.0,
                min=0,
            ),
        ),
    ),
    BlockSpec(
        key="not_within",
        kind="filter",
        cls=_f.NotWithin,
        label="Exclude inside a layer",
        description="Remove parcels that overlap a layer you want to avoid (e.g. a floodplain).",
        params=(
            ParamSpec(
                "layer",
                "layer",
                "Avoid this layer",
                "The map layer to avoid; parcels touching it are removed (e.g. floodplain).",
            ),
        ),
    ),
    BlockSpec(
        key="within",
        kind="filter",
        cls=_f.Within,
        label="Keep inside a layer",
        description="Keep only parcels that fall inside a boundary (e.g. a service area).",
        params=(
            ParamSpec(
                "layer",
                "layer",
                "Must be inside this layer",
                "The boundary layer; only parcels touching it are kept (e.g. a service area).",
            ),
        ),
    ),
    BlockSpec(
        key="attr_in",
        kind="filter",
        cls=_f.AttrIn,
        label="Allowed values",
        description="Keep parcels whose attribute is one of an allowed set (e.g. allowed zoning).",
        params=(
            ParamSpec(
                "field",
                "field",
                "Parcel attribute",
                "The parcel column to check (e.g. zoning).",
            ),
            ParamSpec(
                "values",
                "multiselect",
                "Allowed values",
                "Parcels are kept only if the attribute equals one of these values.",
                default=(),
            ),
        ),
    ),
    BlockSpec(
        key="attr_range",
        kind="filter",
        cls=_f.AttrRange,
        label="Numeric range",
        description="Keep parcels whose numeric attribute falls within a min/max range.",
        params=(
            ParamSpec(
                "field",
                "field",
                "Numeric attribute",
                "The numeric parcel column to check (e.g. assessed value).",
            ),
            ParamSpec(
                "min",
                "number",
                "Minimum",
                "Lowest allowed value (leave blank for no lower limit).",
                required=False,
            ),
            ParamSpec(
                "max",
                "number",
                "Maximum",
                "Highest allowed value (leave blank for no upper limit).",
                required=False,
            ),
        ),
    ),
    # ---- Criteria (weighted scoring) ------------------------------------- #
    BlockSpec(
        key="proximity",
        kind="criterion",
        cls=_s.Proximity,
        label="Proximity to a layer",
        description="Score parcels by how close they are to a layer (e.g. reward being near highways).",
        params=(
            ParamSpec(
                "to",
                "layer",
                "Measure distance to",
                "The layer to measure distance to (e.g. highways, dealers).",
            ),
            ParamSpec(
                "prefer",
                "select",
                "Prefer",
                "'near' rewards parcels closer to the layer; 'far' rewards those farther away.",
                default="near",
                options=_PREFER_NF,
            ),
            ParamSpec(
                "weight",
                "number",
                "Weight",
                "How much this criterion counts. Weights are auto-balanced to sum to 100%.",
                default=1.0,
                min=0,
            ),
        ),
    ),
    BlockSpec(
        key="gap",
        kind="criterion",
        cls=_s.Gap,
        label="Competitor gap",
        description="Reward parcels with few competitors nearby — finds underserved gaps in the market.",
        params=(
            ParamSpec(
                "of",
                "layer",
                "Competitor locations",
                "The layer of competitor sites to count nearby (e.g. existing storage facilities).",
            ),
            ParamSpec(
                "within_mi",
                "number",
                "Search radius (miles)",
                "Competitors within this many miles of a parcel are counted; fewer scores higher.",
                default=5.0,
                min=0,
            ),
            ParamSpec(
                "weight",
                "number",
                "Weight",
                "How much this criterion counts. Weights are auto-balanced to sum to 100%.",
                default=1.0,
                min=0,
            ),
        ),
    ),
    BlockSpec(
        key="index",
        kind="criterion",
        cls=_s.Index,
        label="Index layer / column",
        description="Score from a precomputed index — a parcel column, or a layer joined to parcels (e.g. demand).",
        params=(
            ParamSpec(
                "layer",
                "layer",
                "Index layer",
                "A layer carrying an index value to join onto parcels (e.g. an ACS demand index).",
            ),
            ParamSpec(
                "value_field",
                "text",
                "Value column",
                "Which column in the index layer holds the value (needed if it has more than one).",
                required=False,
            ),
            ParamSpec(
                "prefer",
                "select",
                "Prefer",
                "'high' rewards larger index values; 'low' rewards smaller ones.",
                default="high",
                options=_PREFER_HL,
            ),
            ParamSpec(
                "weight",
                "number",
                "Weight",
                "How much this criterion counts. Weights are auto-balanced to sum to 100%.",
                default=1.0,
                min=0,
            ),
        ),
    ),
    BlockSpec(
        key="attr_value",
        kind="criterion",
        cls=_s.AttrValue,
        label="Parcel attribute value",
        description="Score directly from a numeric parcel attribute (e.g. prefer lower assessed value).",
        params=(
            ParamSpec(
                "field",
                "field",
                "Numeric attribute",
                "The numeric parcel column to score from (e.g. assessed value).",
            ),
            ParamSpec(
                "prefer",
                "select",
                "Prefer",
                "'high' rewards larger values; 'low' rewards smaller ones.",
                default="high",
                options=_PREFER_HL,
            ),
            ParamSpec(
                "weight",
                "number",
                "Weight",
                "How much this criterion counts. Weights are auto-balanced to sum to 100%.",
                default=1.0,
                min=0,
            ),
        ),
    ),
)

_BY_KEY: dict[str, BlockSpec] = {b.key: b for b in REGISTRY}
_BY_CLS: dict[type, BlockSpec] = {b.cls: b for b in REGISTRY}


def get(key: str) -> BlockSpec:
    """Return the :class:`BlockSpec` for a YAML key, or raise a clear error."""
    if key not in _BY_KEY:
        raise ValueError(f"unknown block {key!r}; available: {sorted(_BY_KEY)}.")
    return _BY_KEY[key]


def for_class(cls: type) -> BlockSpec:
    """Return the :class:`BlockSpec` describing a filter/criterion class."""
    if cls not in _BY_CLS:
        raise ValueError(f"{cls.__name__} has no registry entry.")
    return _BY_CLS[cls]


def filters() -> list[BlockSpec]:
    """All filter blocks, in catalog order."""
    return [b for b in REGISTRY if b.kind == "filter"]


def criteria() -> list[BlockSpec]:
    """All criterion blocks, in catalog order."""
    return [b for b in REGISTRY if b.kind == "criterion"]


def all_keys() -> list[str]:
    """Every registered block key."""
    return [b.key for b in REGISTRY]
