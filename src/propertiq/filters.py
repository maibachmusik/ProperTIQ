"""Hard, pass/fail filters. Each drops parcels that fail its predicate.

Implements ``spec 001``. All area/distance math runs in the measurement CRS;
user-supplied layers are CRS-aligned (and warned-on) before any spatial join.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Sequence

from .crs import ensure_aligned
from .strategy import Filter

if TYPE_CHECKING:
    import geopandas as gpd

_SQM_PER_ACRE = 4046.8564224
_METERS_PER_MILE = 1609.344

# Cardinal / intercardinal direction → aspect degrees (0 = North, clockwise).
_FACING_DEG = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}


def _require_field(parcels: "gpd.GeoDataFrame", field: str) -> None:
    if field not in parcels.columns:
        raise KeyError(
            f"field {field!r} not found in parcels; available columns: {list(parcels.columns)}"
        )


@dataclass
class MinArea(Filter):
    """Keep parcels at least ``acres`` in size (computed in the measurement CRS)."""

    acres: float

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        acres = parcels.geometry.area / _SQM_PER_ACRE
        return parcels[acres >= self.acres]


@dataclass
class MaxArea(Filter):
    """Keep parcels no larger than ``acres``."""

    acres: float

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        acres = parcels.geometry.area / _SQM_PER_ACRE
        return parcels[acres <= self.acres]


@dataclass
class NotWithin(Filter):
    """Drop parcels intersecting ``layer`` (e.g. a floodplain)."""

    layer: Any  # GeoDataFrame

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        import geopandas as gpd

        (layer,) = ensure_aligned(self.layer, crs=crs)
        hits = gpd.sjoin(parcels, layer[[layer.geometry.name]], predicate="intersects", how="inner")
        return parcels[~parcels.index.isin(hits.index)]


@dataclass
class Within(Filter):
    """Keep only parcels intersecting ``layer`` (e.g. a service-area boundary)."""

    layer: Any  # GeoDataFrame

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        import geopandas as gpd

        (layer,) = ensure_aligned(self.layer, crs=crs)
        hits = gpd.sjoin(parcels, layer[[layer.geometry.name]], predicate="intersects", how="inner")
        return parcels[parcels.index.isin(hits.index)]


@dataclass
class AttrIn(Filter):
    """Keep parcels whose ``field`` is one of ``values`` (e.g. allowed zoning)."""

    field: str
    values: Sequence[Any]

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        _require_field(parcels, self.field)
        return parcels[parcels[self.field].isin(list(self.values))]


@dataclass
class AttrRange(Filter):
    """Keep parcels whose numeric ``field`` falls within [min, max]."""

    field: str
    min: float | None = None
    max: float | None = None

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        import pandas as pd

        _require_field(parcels, self.field)
        col = pd.to_numeric(parcels[self.field], errors="coerce")
        keep = col.notna()
        if self.min is not None:
            keep &= col >= self.min
        if self.max is not None:
            keep &= col <= self.max
        return parcels[keep]


@dataclass
class WithinDistance(Filter):
    """Keep parcels within ``max_mi`` miles of any feature in ``layer``.

    Use for access rules: near a road, a utility line, or a water feature.
    """

    layer: Any  # GeoDataFrame
    max_mi: float = 1.0

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        (layer,) = ensure_aligned(self.layer, crs=crs)
        if len(layer) == 0:
            raise ValueError("WithinDistance layer is empty.")
        dist = parcels.geometry.distance(layer.geometry.union_all())
        return parcels[dist <= self.max_mi * _METERS_PER_MILE]


@dataclass
class CountRange(Filter):
    """Keep parcels with a feature count in ``[min, max]`` within ``within_mi``.

    ``within_mi=0`` counts features intersecting the parcel itself — e.g.
    ``max=0`` keeps vacant parcels (no structures); ``min=5`` keeps built-up ones.
    """

    of: Any  # GeoDataFrame
    within_mi: float = 0.0
    min: float | None = None
    max: float | None = None

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        counts = _count_nearby(parcels, self.of, self.within_mi, crs)
        keep = counts.notna()
        if self.min is not None:
            keep &= counts >= self.min
        if self.max is not None:
            keep &= counts <= self.max
        return parcels[keep.values]


@dataclass
class Facing(Filter):
    """Keep parcels whose mean aspect faces ``direction`` within ``tolerance_deg``.

    ``field`` is a numeric aspect column in degrees (0 = North, clockwise). The
    check is circular, so ``direction='N'`` spans 337.5–22.5°. Parcels with no
    aspect (flat / missing terrain) are dropped.
    """

    direction: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"] = "S"
    tolerance_deg: float = 45.0
    field: str = "aspect_deg"

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        import pandas as pd

        _require_field(parcels, self.field)
        key = self.direction.upper()
        if key not in _FACING_DEG:
            raise ValueError(
                f"unknown direction {self.direction!r}; use one of {list(_FACING_DEG)}."
            )
        center = _FACING_DEG[key]
        aspect = pd.to_numeric(parcels[self.field], errors="coerce")
        # Smallest circular difference between aspect and the target bearing.
        diff = ((aspect - center + 180.0) % 360.0 - 180.0).abs()
        return parcels[diff <= self.tolerance_deg]


def _count_nearby(parcels: "gpd.GeoDataFrame", layer: Any, within_mi: float, crs: str):
    """Count features of ``layer`` within ``within_mi`` of each parcel (0 = intersecting)."""
    import geopandas as gpd
    import pandas as pd

    (layer,) = ensure_aligned(layer, crs=crs)
    if within_mi and within_mi > 0:
        target = parcels.copy()
        target[target.geometry.name] = parcels.geometry.buffer(within_mi * _METERS_PER_MILE)
    else:
        target = parcels
    joined = gpd.sjoin(
        target[[target.geometry.name]],
        layer[[layer.geometry.name]],
        predicate="intersects",
        how="left",
    )
    counts = joined.groupby(joined.index)["index_right"].count()
    return pd.Series(counts, index=parcels.index, name="count").fillna(0)
