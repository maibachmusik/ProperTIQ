"""I/O: read/write GeoDataFrames and load YAML strategies.

Skeleton — see ``spec: yaml-strategies``.
"""

from __future__ import annotations

from typing import Any


def load_strategy(path: str) -> "Any":
    """Parse a YAML strategy file into a :class:`propertiq.Strategy`."""
    raise NotImplementedError


def to_file(gdf: "Any", path: str) -> None:
    """Write candidates to GeoJSON or GeoParquet, inferred from the extension."""
    raise NotImplementedError
