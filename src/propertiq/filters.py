"""Hard, pass/fail filters. Each drops parcels that fail its predicate.

Implements ``spec 001``. All area/distance math runs in the measurement CRS;
user-supplied layers are CRS-aligned (and warned-on) before any spatial join.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

from .crs import ensure_aligned
from .strategy import Filter

if TYPE_CHECKING:
    import geopandas as gpd

_SQM_PER_ACRE = 4046.8564224


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
