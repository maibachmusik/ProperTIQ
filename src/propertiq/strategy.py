"""Strategy composition, execution, and results.

Skeleton only — signatures and docstrings define the v0.1 contract; the scoring
engine is implemented in ``spec: scoring-core``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

# NOTE: geopandas is imported lazily inside methods so importing the package is
# cheap and doesn't hard-require the geo stack until you actually run a strategy.


class Filter:
    """Base class for hard, pass/fail constraints. Subclasses live in ``filters``."""

    def apply(self, parcels: "Any") -> "Any":  # -> GeoDataFrame
        raise NotImplementedError


class Criterion:
    """Base class for weighted scoring signals. Subclasses live in ``scoring``."""

    weight: float

    def score(self, parcels: "Any") -> "Any":  # -> pd.Series in [0, 1]
        raise NotImplementedError


@dataclass
class Strategy:
    """A declarative site-selection strategy.

    Parameters
    ----------
    filters:
        Hard, pass/fail constraints. A parcel must satisfy all of them to survive.
    score:
        Weighted scoring criteria. Weights are auto-normalized to sum to 1.0.
    name:
        Optional label, surfaced in exports and explanations.
    """

    filters: Sequence[Filter] = field(default_factory=list)
    score: Sequence[Criterion] = field(default_factory=list)
    name: str | None = None

    def run(self, parcels: "Any", *, measurement_crs: str = "EPSG:5070") -> "Result":
        """Apply filters, score survivors, rank, and return a :class:`Result`.

        All area/distance math runs in ``measurement_crs`` (default EPSG:5070,
        CONUS Albers Equal Area). Inputs are reprojected and validated first.
        """
        raise NotImplementedError("scoring engine — see spec: scoring-core")


@dataclass
class Result:
    """The outcome of a run: scored, ranked candidates with explanations."""

    parcels: "Any"  # GeoDataFrame with score, rank, score_breakdown columns
    strategy: Strategy

    def top(self, n: int = 20) -> "Any":
        """Return the ``n`` highest-scoring candidates."""
        raise NotImplementedError

    def explain(self) -> "Any":
        """Return a per-criterion contribution table for the candidates."""
        raise NotImplementedError

    def to_map(self):
        """Render an interactive map (folium; leafmap via the ``[viz]`` extra)."""
        raise NotImplementedError

    def to_file(self, path: str) -> None:
        """Export candidates to GeoJSON or GeoParquet (by extension)."""
        raise NotImplementedError


def run(strategy: "str | Strategy", parcels: "Any", *, layers: dict[str, Any] | None = None) -> Result:
    """Run a strategy given as a :class:`Strategy` or a path to a YAML file.

    ``layers`` maps the named layers referenced in a YAML strategy (e.g.
    ``fema_floodplain``, ``highways``) to GeoDataFrames.
    """
    raise NotImplementedError("YAML loader — see spec: yaml-strategies")
