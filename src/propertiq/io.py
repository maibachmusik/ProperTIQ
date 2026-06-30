"""I/O: write scored candidates to open formats; load/dump YAML strategies.

Implements ``spec 001`` export (FR-7) and ``spec 002`` YAML round-trip (FR-C4).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import geopandas as gpd

    from .strategy import Strategy


def load_strategy(path: str, layers: dict[str, Any] | None = None) -> "Strategy":
    """Parse a YAML strategy file into a :class:`propertiq.Strategy`.

    ``layers`` maps the layer names referenced in the file (e.g. ``highways``,
    ``fema_floodplain``) to GeoDataFrames.
    """
    import yaml

    from .config import from_config

    with open(path) as fh:
        config = yaml.safe_load(fh)
    return from_config(config, layers=layers)


def dump_strategy(
    strategy: "Strategy", path: str, layer_names: dict[int, str] | None = None
) -> None:
    """Serialize a :class:`Strategy` to a YAML file (see ``config.to_config``)."""
    import yaml

    from .config import to_config

    with open(path, "w") as fh:
        yaml.safe_dump(to_config(strategy, layer_names=layer_names), fh, sort_keys=False)


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
