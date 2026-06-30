"""Map rendering for results. folium is the core engine (PRD N-4); leafmap is an
optional ``[viz]`` extra for later.

Implements ``spec 004`` (FR-9). Keeps the no-black-box promise on the map: each
parcel's tooltip shows its score, rank, and per-criterion contribution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import folium
    import geopandas as gpd


def _import_folium():
    try:
        import folium  # noqa: F401

        return folium
    except ImportError as exc:  # pragma: no cover - exercised only without folium
        raise ImportError(
            "folium is required for maps. It ships with the core install; "
            "reinstall with `pip install propertiq` (or `propertiq[viz]`)."
        ) from exc


def _resolve_colormap(cmap: str):
    """Resolve a colorbrewer name (e.g. 'YlGn') to a branca colormap.

    branca registers numbered variants ('YlGn_09'); accept the bare name and pick
    the richest (most-colors) variant.
    """
    import branca.colormap as bcm

    cmaps = bcm.linear._colormaps
    if cmap in cmaps:
        return bcm.linear._colormaps[cmap]
    matches = sorted(
        (k for k in cmaps if k.startswith(f"{cmap}_")),
        key=lambda k: int(k.rsplit("_", 1)[-1]) if k.rsplit("_", 1)[-1].isdigit() else 0,
    )
    if matches:
        return cmaps[matches[-1]]
    raise ValueError(f"unknown colormap {cmap!r}; see branca.colormap.linear.")


def _format_breakdown(value: Any) -> str:
    """Render a per-parcel breakdown dict as a compact 'criterion: contribution' string."""
    if isinstance(value, dict):
        return " · ".join(f"{k}: {v:.1f}" for k, v in value.items())
    return str(value)


def to_map(
    candidates: "gpd.GeoDataFrame",
    *,
    column: str = "score",
    n: int | None = None,
    cmap: str = "YlGn",
    tiles: str = "CartoDB positron",
    tooltip_fields: list[str] | None = None,
) -> "folium.Map":
    """Render scored candidates as an interactive folium map (see ``spec 004``)."""
    import folium

    if len(candidates) == 0:
        raise ValueError("no candidates to map.")
    if column not in candidates.columns:
        raise KeyError(f"column {column!r} not found; available: {list(candidates.columns)}")

    gdf = candidates if n is None else candidates.head(n)
    gdf = gdf.to_crs(4326)

    # Color scale: scores are absolute 0–100; any other column uses its own range.
    values = gdf[column].astype(float)
    vmin, vmax = (0.0, 100.0) if column == "score" else (float(values.min()), float(values.max()))
    if vmax <= vmin:
        vmax = vmin + 1.0
    colormap = _resolve_colormap(cmap).scale(vmin, vmax)
    colormap.caption = column

    minx, miny, maxx, maxy = gdf.total_bounds
    fmap = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], tiles=tiles, zoom_start=12)

    # Build a readable breakdown column for the tooltip.
    show = gdf.copy()
    fields = ["rank", column] if column != "rank" else ["rank"]
    for extra in tooltip_fields or []:
        if extra in show.columns and extra not in fields:
            fields.append(extra)
    if "score_breakdown" in show.columns:
        show["why"] = show["score_breakdown"].apply(_format_breakdown)
        fields.append("why")
    # Drop columns folium can't serialize (dicts) before handing it the GeoJSON.
    drop = [c for c in show.columns if c == "score_breakdown" or c.startswith("signal__")]
    show = show.drop(columns=drop)
    fields = [f for f in fields if f in show.columns]

    def style(feature: dict) -> dict:
        val = feature["properties"].get(column)
        color = colormap(float(val)) if val is not None else "#cccccc"
        return {"fillColor": color, "color": color, "weight": 1, "fillOpacity": 0.6}

    folium.GeoJson(
        show,
        style_function=style,
        marker=folium.CircleMarker(radius=6, fill=True),
        tooltip=folium.GeoJsonTooltip(fields=fields),
    ).add_to(fmap)
    colormap.add_to(fmap)
    fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    return fmap
