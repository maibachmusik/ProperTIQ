"""CRS handling: reproject to a metric measurement CRS, validate geometry, warn
on mismatches. Never silently join layers in different CRSs.

Implements ``spec 001`` CRS rules (folds in ``spec: crs-handling``).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd

DEFAULT_MEASUREMENT_CRS = "EPSG:5070"  # NAD83 / CONUS Albers Equal Area


def to_measurement_crs(
    gdf: "gpd.GeoDataFrame", crs: str = DEFAULT_MEASUREMENT_CRS
) -> "gpd.GeoDataFrame":
    """Reproject ``gdf`` to ``crs`` for area/distance math, repairing geometry.

    A ``GeoDataFrame`` with no CRS set is rejected: an unknown CRS cannot be
    measured or reprojected safely.
    """
    if gdf.crs is None:
        raise ValueError(
            "input GeoDataFrame has no CRS set; set a CRS first "
            "(e.g. gdf.set_crs('EPSG:4326')) — an unknown CRS cannot be measured safely."
        )
    out = gdf.to_crs(crs)
    # Repair invalid geometry (self-intersections, etc.) so area/distance is sound.
    invalid = ~out.geometry.is_valid
    if bool(invalid.any()):
        out = out.copy()
        out.loc[invalid, out.geometry.name] = out.geometry[invalid].make_valid()
    return out


def ensure_aligned(
    *gdfs: "gpd.GeoDataFrame", crs: str = DEFAULT_MEASUREMENT_CRS
) -> tuple["gpd.GeoDataFrame", ...]:
    """Reproject every input to a common ``crs``, warning where it differed.

    Use before any spatial op that joins a user-supplied layer to the parcels, so
    mismatched CRSs are reprojected and surfaced — never silently joined.
    """
    aligned = []
    for i, gdf in enumerate(gdfs):
        if gdf.crs is None:
            raise ValueError(
                f"layer #{i} has no CRS set; set a CRS before using it in a filter or criterion."
            )
        if str(gdf.crs) != str(crs):
            warnings.warn(
                f"layer #{i} is in {gdf.crs}; reprojecting to {crs} for alignment.",
                stacklevel=2,
            )
            gdf = gdf.to_crs(crs)
        aligned.append(gdf)
    return tuple(aligned)
