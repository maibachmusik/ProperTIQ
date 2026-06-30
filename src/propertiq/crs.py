"""CRS handling: reproject to a metric measurement CRS, validate geometry, warn
on mismatches. Never silently join layers in different CRSs.

Skeleton — see ``spec: crs-handling``.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MEASUREMENT_CRS = "EPSG:5070"  # NAD83 / CONUS Albers Equal Area


def to_measurement_crs(gdf: "Any", crs: str = DEFAULT_MEASUREMENT_CRS) -> "Any":
    """Reproject ``gdf`` to ``crs`` for area/distance math, validating geometry."""
    raise NotImplementedError


def ensure_aligned(*gdfs: "Any", crs: str = DEFAULT_MEASUREMENT_CRS) -> "tuple":
    """Reproject all inputs to a common ``crs``, warning where they differed."""
    raise NotImplementedError
