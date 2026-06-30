"""Weighted scoring criteria. Each returns a normalized [0, 1] signal per parcel;
the engine combines them by weight into a 0-100 score.

Skeleton — signatures define the v0.1 contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .strategy import Criterion


@dataclass
class Proximity(Criterion):
    """Score by distance to ``to``. ``prefer='near'`` rewards closeness."""

    to: Any  # GeoDataFrame
    weight: float = 1.0
    prefer: Literal["near", "far"] = "near"


@dataclass
class Gap(Criterion):
    """Competitor-gap: reward low density of ``of`` within ``within_mi`` miles."""

    of: Any  # GeoDataFrame of competitor points
    within_mi: float = 5.0
    weight: float = 1.0


@dataclass
class Index(Criterion):
    """Score from a precomputed index layer/column (e.g. an ACS demand index)."""

    layer: Any  # GeoDataFrame or column reference
    weight: float = 1.0


@dataclass
class AttrValue(Criterion):
    """Score directly from a numeric parcel attribute (normalized)."""

    field: str
    weight: float = 1.0
    prefer: Literal["high", "low"] = "high"
