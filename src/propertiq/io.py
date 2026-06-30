"""I/O: write scored candidates to open formats; (v0.2) load YAML strategies.

Implements ``spec 001`` export (FR-7). The YAML loader is deferred to spec 003.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd


def load_strategy(path: str) -> object:
    """Parse a YAML strategy file into a :class:`propertiq.Strategy`."""
    raise NotImplementedError("YAML loader lands in v0.2 — see spec 003: yaml-strategies.")


def to_file(gdf: "gpd.GeoDataFrame", path: str) -> None:
    """Write candidates to GeoJSON or GeoParquet, inferred from the extension.

    GeoJSON is reprojected to EPSG:4326 (the GeoJSON standard); GeoParquet keeps
    the measurement CRS. The ``score_breakdown`` dict is serialized to a JSON
    string so it survives both formats.
    """
    suffix = Path(path).suffix.lower()
    out = gdf.copy()
    if "score_breakdown" in out.columns:
        out["score_breakdown"] = out["score_breakdown"].apply(
            lambda v: json.dumps(v, separators=(",", ":")) if isinstance(v, dict) else v
        )

    if suffix in (".geojson", ".json"):
        if out.crs is not None and str(out.crs) != "EPSG:4326":
            out = out.to_crs("EPSG:4326")
        out.to_file(path, driver="GeoJSON")
    elif suffix == ".parquet":
        out.to_parquet(path)
    else:
        raise ValueError(
            f"unsupported export extension {suffix!r}; use .geojson, .json, or .parquet."
        )
