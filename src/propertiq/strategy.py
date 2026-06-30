"""Strategy composition, execution, and results — the scoring engine.

Implements ``spec 001`` (scoring-core). The pipeline is: normalize CRS → filter →
score (min-max normalize each criterion, apply ``prefer``) → combine by weight →
rank. Every score decomposes into a ``score_breakdown`` that sums to the score
(constitution principle 1 — no black box).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

from .crs import DEFAULT_MEASUREMENT_CRS, to_measurement_crs

if TYPE_CHECKING:
    import geopandas as gpd
    import pandas as pd


class Filter:
    """Base class for hard, pass/fail constraints. Subclasses live in ``filters``."""

    def apply(self, parcels: "gpd.GeoDataFrame", crs: str) -> "gpd.GeoDataFrame":
        """Return the subset of ``parcels`` that satisfies this constraint."""
        raise NotImplementedError


class Criterion:
    """Base class for weighted scoring signals. Subclasses live in ``scoring``.

    A criterion produces one *raw* value per parcel via :meth:`raw`; the engine
    min-max normalizes it across the candidate set and applies ``prefer``.
    """

    weight: float = 1.0
    prefer: str = "high"
    name: str | None = None

    def raw(self, parcels: "gpd.GeoDataFrame", crs: str) -> "pd.Series":
        """Return the raw per-parcel signal (higher = more of the thing measured)."""
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Engine helpers (module-private)
# --------------------------------------------------------------------------- #
def _normalize_weights(criteria: Sequence[Criterion]) -> list[float]:
    """Normalize criterion weights to sum to 1.0. Reject empty / non-positive."""
    if not criteria:
        raise ValueError("a Strategy needs at least one scoring criterion to rank parcels.")
    weights = [float(getattr(c, "weight", 1.0)) for c in criteria]
    if any(w < 0 for w in weights):
        raise ValueError("criterion weights must be non-negative.")
    total = sum(weights)
    if total <= 0:
        raise ValueError("criterion weights sum to zero; at least one must be positive.")
    return [w / total for w in weights]


def _minmax(raw: "pd.Series") -> "pd.Series":
    """Min-max normalize to [0, 1] over the candidate set.

    Degenerate range (all equal, or a single parcel) → neutral 0.5 everywhere.
    Missing values are excluded from the min/max and get signal 0 (worst).
    """
    import pandas as pd

    raw = pd.to_numeric(raw, errors="coerce")
    valid = raw.dropna()
    if valid.empty:
        return pd.Series(0.0, index=raw.index, dtype="float64")
    lo, hi = float(valid.min()), float(valid.max())
    if hi == lo:
        out = pd.Series(0.5, index=raw.index, dtype="float64")
    else:
        out = (raw - lo) / (hi - lo)
    return out.fillna(0.0).clip(0.0, 1.0)


def _apply_prefer(norm: "pd.Series", prefer: str) -> "pd.Series":
    """Flip the normalized signal so that higher always means 'better'."""
    if prefer in ("near", "low"):
        return 1.0 - norm
    if prefer in ("far", "high"):
        return norm
    raise ValueError(f"unknown prefer={prefer!r}; expected one of near/far/high/low.")


def _resolve_names(criteria: Sequence[Criterion]) -> list[str]:
    """Stable, unique breakdown keys: explicit ``name`` wins; repeats get _2, _3."""
    names: list[str] = []
    seen: dict[str, int] = {}
    for c in criteria:
        base = c.name or type(c).__name__
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return names


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

    def run(
        self, parcels: "gpd.GeoDataFrame", *, measurement_crs: str = DEFAULT_MEASUREMENT_CRS
    ) -> "Result":
        """Apply filters, score survivors, rank, and return a :class:`Result`.

        All area/distance math runs in ``measurement_crs`` (default EPSG:5070,
        CONUS Albers Equal Area). Inputs are reprojected and validated first.
        """
        import pandas as pd

        gdf = to_measurement_crs(parcels, measurement_crs)
        for f in self.filters:
            gdf = f.apply(gdf, measurement_crs)

        weights = _normalize_weights(self.score)
        names = _resolve_names(self.score)

        gdf = gdf.copy()
        contribs: dict[str, "pd.Series"] = {}
        if len(gdf) == 0:
            # No survivors: emit empty score columns so the shape is stable.
            for name in names:
                gdf[f"signal__{name}"] = pd.Series(dtype="float64")
            gdf["score"] = pd.Series(dtype="float64")
            gdf["rank"] = pd.Series(dtype="int64")
            gdf["score_breakdown"] = pd.Series(dtype="object")
            return Result(parcels=gdf, strategy=self)

        for crit, w, name in zip(self.score, weights, names):
            raw = crit.raw(gdf, measurement_crs)
            raw.index = gdf.index
            signal = _apply_prefer(_minmax(raw), crit.prefer)
            gdf[f"signal__{name}"] = signal
            contribs[name] = 100.0 * w * signal

        score_series = sum(contribs.values())
        gdf["score"] = score_series
        gdf["score_breakdown"] = [
            {name: float(contribs[name].iloc[i]) for name in names} for i in range(len(gdf))
        ]
        gdf = gdf.sort_values("score", ascending=False, kind="stable")
        gdf["rank"] = range(1, len(gdf) + 1)
        return Result(parcels=gdf, strategy=self)

    def to_config(self, layer_names: "dict[int, str] | None" = None) -> dict[str, Any]:
        """Serialize this strategy to a config dict (see :mod:`propertiq.config`)."""
        from .config import to_config

        return to_config(self, layer_names=layer_names)


@dataclass
class Result:
    """The outcome of a run: scored, ranked candidates with explanations."""

    parcels: "gpd.GeoDataFrame"  # has score, rank, score_breakdown, signal__* cols
    strategy: Strategy

    def top(self, n: int = 20) -> "gpd.GeoDataFrame":
        """Return the ``n`` highest-ranked candidates (already sorted best-first)."""
        return self.parcels.head(n)

    def explain(self) -> "pd.DataFrame":
        """Per-criterion contribution table: one row per candidate, one column per
        criterion, plus the total ``score``. Contributions sum to ``score``."""
        import pandas as pd

        rows = self.parcels["score_breakdown"].tolist() if len(self.parcels) else []
        table = pd.DataFrame(rows, index=self.parcels.index)
        table["score"] = self.parcels["score"].values
        if "rank" in self.parcels:
            table.insert(0, "rank", self.parcels["rank"].values)
        return table

    def to_map(self):
        """Render an interactive map (folium; leafmap via the ``[viz]`` extra)."""
        raise NotImplementedError("map rendering lands in v0.2 (spec: viz).")

    def to_file(self, path: str) -> None:
        """Export candidates to GeoJSON or GeoParquet (by extension)."""
        from .io import to_file

        to_file(self.parcels, path)


def run(
    strategy: "str | Strategy", parcels: "Any", *, layers: dict[str, Any] | None = None
) -> Result:
    """Run a strategy given as a :class:`Strategy` or a path to a YAML file.

    ``layers`` maps the named layers referenced in a YAML strategy (e.g.
    ``fema_floodplain``, ``highways``) to GeoDataFrames.
    """
    if isinstance(strategy, Strategy):
        return strategy.run(parcels)
    if isinstance(strategy, dict):
        from .config import from_config

        return from_config(strategy, layers=layers).run(parcels)
    if isinstance(strategy, str):
        from .io import load_strategy

        return load_strategy(strategy, layers=layers).run(parcels)
    raise TypeError(
        f"strategy must be a Strategy, a config dict, or a path to a YAML file; "
        f"got {type(strategy).__name__}."
    )


def _breakdown_to_json(value: Any) -> str:
    """Serialize a per-parcel breakdown dict to a compact JSON string (for export)."""
    return json.dumps(value, separators=(",", ":"))
