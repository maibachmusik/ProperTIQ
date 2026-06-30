"""ProperTIQ — site suitability as code.

Declare a weighted site-selection strategy, run it over your parcels, and get
ranked candidates back with a transparent, per-criterion score breakdown.

This is an alpha scaffold: the public API is defined here and in ``docs/PRD.md``;
the scoring engine is being implemented toward ``v0.1``.
"""

from __future__ import annotations

__version__ = "0.0.1.dev0"

from .strategy import Strategy, Result, run
from .filters import MinArea, MaxArea, NotWithin, Within, AttrIn, AttrRange
from .scoring import Proximity, Gap, Index, AttrValue

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
    # scoring
    "Proximity",
    "Gap",
    "Index",
    "AttrValue",
]
