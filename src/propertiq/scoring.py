"""Weighted scoring criteria. Each returns a *raw* per-parcel value; the engine
min-max normalizes it across the candidate set, applies ``prefer``, and combines
criteria by weight into a 0-100 score.

Implements ``spec 001``. User-supplied layers are CRS-aligned before any spatial op.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from .crs import ensure_aligned
from .strategy import Criterion

if TYPE_CHECKING:
    import geopandas as gpd
    import pandas as pd

_METERS_PER_MILE = 1609.344


@dataclass
class Proximity(Criterion):
    """Score by distance to ``to``. ``prefer='near'`` rewards closeness."""

    to: Any  # GeoDataFrame
    weight: float = 1.0
    prefer: Literal["near", "far"] = "near"
    name: str | None = None

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        import pandas as pd

        (layer,) = ensure_aligned(self.to, crs=crs)
        if len(layer) == 0:
            raise ValueError("Proximity target layer 'to' is empty.")
        target = layer.geometry.union_all()
        return pd.Series(parcels.geometry.distance(target), index=parcels.index, name="distance")


@dataclass
class Gap(Criterion):
    """Competitor-gap: reward low density of ``of`` within ``within_mi`` miles.

    Always behaves as ``prefer='low'`` — fewer competitors nearby scores higher.
    """

    of: Any  # GeoDataFrame of competitor points
    within_mi: float = 5.0
    weight: float = 1.0
    name: str | None = None
    prefer: str = "low"

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        import geopandas as gpd
        import pandas as pd

        (layer,) = ensure_aligned(self.of, crs=crs)
        radius_m = self.within_mi * _METERS_PER_MILE
        buffered = parcels.copy()
        buffered[buffered.geometry.name] = parcels.geometry.buffer(radius_m)
        joined = gpd.sjoin(
            buffered[[buffered.geometry.name]],
            layer[[layer.geometry.name]],
            predicate="intersects",
            how="left",
        )
        counts = joined.groupby(joined.index)["index_right"].count()
        return pd.Series(counts, index=parcels.index, name="competitor_count").fillna(0)


@dataclass
class NearbyCount(Criterion):
    """Score by how many features of ``of`` are within ``within_mi`` of a parcel.

    ``prefer='high'`` rewards density (built-up areas, nearby amenities);
    ``prefer='low'`` rewards isolation. (``Gap`` is the competitor-specific
    ``prefer='low'`` case.)
    """

    of: Any  # GeoDataFrame
    within_mi: float = 1.0
    weight: float = 1.0
    prefer: Literal["high", "low"] = "high"
    name: str | None = None

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        import geopandas as gpd
        import pandas as pd

        (layer,) = ensure_aligned(self.of, crs=crs)
        target = parcels.copy()
        if self.within_mi and self.within_mi > 0:
            target[target.geometry.name] = parcels.geometry.buffer(
                self.within_mi * _METERS_PER_MILE
            )
        joined = gpd.sjoin(
            target[[target.geometry.name]],
            layer[[layer.geometry.name]],
            predicate="intersects",
            how="left",
        )
        counts = joined.groupby(joined.index)["index_right"].count()
        return pd.Series(counts, index=parcels.index, name="nearby_count").fillna(0)


@dataclass
class Index(Criterion):
    """Score from a precomputed index: a column already on the parcels, or a
    layer spatially joined to them."""

    layer: Any  # column name (str) OR GeoDataFrame
    weight: float = 1.0
    value_field: str | None = None
    prefer: Literal["high", "low"] = "high"
    name: str | None = None

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        import geopandas as gpd
        import pandas as pd

        if isinstance(self.layer, str):
            if self.layer not in parcels.columns:
                raise KeyError(f"Index column {self.layer!r} not found on parcels.")
            return pd.to_numeric(parcels[self.layer], errors="coerce")

        (layer,) = ensure_aligned(self.layer, crs=crs)
        field = self._resolve_value_field(layer)
        joined = gpd.sjoin(
            parcels[[parcels.geometry.name]],
            layer[[field, layer.geometry.name]],
            predicate="intersects",
            how="left",
        )
        # A parcel can intersect several index polygons; take the mean value.
        values = pd.to_numeric(joined[field], errors="coerce").groupby(joined.index).mean()
        return values.reindex(parcels.index)

    def _resolve_value_field(self, layer: "gpd.GeoDataFrame") -> str:
        if self.value_field is not None:
            if self.value_field not in layer.columns:
                raise KeyError(f"value_field {self.value_field!r} not in index layer.")
            return self.value_field
        import pandas as pd

        numeric = [
            c
            for c in layer.columns
            if c != layer.geometry.name and pd.api.types.is_numeric_dtype(layer[c])
        ]
        if len(numeric) != 1:
            raise ValueError(
                "Index layer has "
                f"{len(numeric)} numeric columns {numeric}; pass value_field= to pick one."
            )
        return numeric[0]


@dataclass
class AttrValue(Criterion):
    """Score directly from a numeric parcel attribute (normalized)."""

    field: str
    weight: float = 1.0
    prefer: Literal["high", "low"] = "high"
    name: str | None = None

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        import pandas as pd

        if self.field not in parcels.columns:
            raise KeyError(f"AttrValue field {self.field!r} not found on parcels.")
        return pd.to_numeric(parcels[self.field], errors="coerce")
