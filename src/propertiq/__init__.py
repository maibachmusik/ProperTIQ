"""ProperTIQ — site suitability as code.

Declare a weighted site-selection strategy, run it over your parcels, and get
ranked candidates back with a transparent, per-criterion score breakdown.

This is an alpha scaffold: the public API is defined here and in ``docs/PRD.md``;
the scoring engine is being implemented toward ``v0.1``.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .strategy import Strategy, Result, run
from .filters import (
    MinArea,
    MaxArea,
    NotWithin,
    Within,
    AttrIn,
    AttrRange,
    WithinDistance,
    CountRange,
    Facing,
)
from .scoring import Proximity, Gap, Index, AttrValue, NearbyCount
from .config import from_config, to_config
from .io import load_strategy, dump_strategy, to_file
from . import registry

__all__ = [
    "Strategy",
    "Result",
    "run",
    # filters
    "MinArea",
    "MaxArea",
    "NotWithin",
    "Within",
    "AttrIn",
    "AttrRange",
    "WithinDistance",
    "CountRange",
    "Facing",
    # scoring
    "Proximity",
    "Gap",
    "Index",
    "AttrValue",
    "NearbyCount",
    # config / registry
    "from_config",
    "to_config",
    "load_strategy",
    "dump_strategy",
    "to_file",
    "registry",
]
