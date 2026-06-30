"""Hard, pass/fail filters. Each drops parcels that fail its predicate.

Skeleton — signatures define the v0.1 contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .strategy import Filter


@dataclass
class MinArea(Filter):
    """Keep parcels at least ``acres`` in size (computed in the measurement CRS)."""

    acres: float


@dataclass
class MaxArea(Filter):
    """Keep parcels no larger than ``acres``."""

    acres: float


@dataclass
class NotWithin(Filter):
    """Drop parcels intersecting ``layer`` (e.g. a floodplain)."""

    layer: Any  # GeoDataFrame


@dataclass
class Within(Filter):
    """Keep only parcels intersecting ``layer`` (e.g. a service-area boundary)."""

    layer: Any  # GeoDataFrame


@dataclass
class AttrIn(Filter):
    """Keep parcels whose ``field`` is one of ``values`` (e.g. allowed zoning)."""

    field: str
    values: Sequence[Any]


@dataclass
class AttrRange(Filter):
    """Keep parcels whose numeric ``field`` falls within [min, max]."""

    field: str
    min: float | None = None
    max: float | None = None
