"""Ready-made starter strategies for the config app.

Each preset is an ordinary ProperTIQ config (the same format the app exports and
``pq.run`` consumes), plus display metadata and the data it expects. Selecting one
populates the builder so a user can tune and run it immediately.

``needs`` lists the parcel columns / layer names a preset references. Columns like
``slope_deg`` / ``aspect_deg`` come from the fast terrain load; ``buildings`` and
``structures`` come from the on-demand "structures & site layers" button.
"""

from __future__ import annotations

PRESETS: list[dict] = [
    {
        "key": "buildable_land",
        "label": "🏗 Buildable land",
        "desc": "Flat, outside the floodplain, with road access — general build-site screen.",
        "needs": ["slope_deg", "floodplain", "highways"],
        "config": {
            "name": "buildable_land",
            "filters": [
                {"attr_range": {"field": "slope_deg", "max": 15}},
                {"not_within": {"layer": "floodplain"}},
                {"within_distance": {"layer": "highways", "max_mi": 1.0}},
            ],
            "score": [
                {"attr_value": {"field": "slope_deg", "prefer": "low", "weight": 0.5}},
                {"proximity": {"to": "highways", "prefer": "near", "weight": 0.5}},
            ],
        },
    },
    {
        "key": "rv_boat_storage",
        "label": "🚐 RV / boat storage",
        "desc": "Larger parcels, out of the floodplain, near a highway with room to expand.",
        "needs": ["acres", "floodplain", "highways"],
        "config": {
            "name": "rv_boat_storage",
            "filters": [
                {"min_area": {"acres": 1}},
                {"not_within": {"layer": "floodplain"}},
                {"within_distance": {"layer": "highways", "max_mi": 1.0}},
            ],
            "score": [
                {"proximity": {"to": "highways", "prefer": "near", "weight": 0.5}},
                {"attr_value": {"field": "acres", "prefer": "high", "weight": 0.5}},
            ],
        },
    },
    {
        "key": "south_facing_homesite",
        "label": "🧭 South-facing homesite",
        "desc": "South-facing, gently sloped land set back from the highway.",
        "needs": ["aspect_deg", "slope_deg", "highways"],
        "config": {
            "name": "south_facing_homesite",
            "filters": [
                {"facing": {"direction": "S", "tolerance_deg": 45}},
                {"attr_range": {"field": "slope_deg", "max": 20}},
            ],
            "score": [
                {"attr_value": {"field": "slope_deg", "prefer": "low", "weight": 0.6}},
                {"proximity": {"to": "highways", "prefer": "far", "weight": 0.4}},
            ],
        },
    },
    {
        "key": "vacant_land",
        "label": "🌳 Vacant land",
        "desc": "No structures on the parcel, out of the floodplain (needs the structures layer).",
        "needs": ["buildings", "floodplain", "acres"],
        "config": {
            "name": "vacant_land",
            "filters": [
                {"count_range": {"of": "buildings", "within_mi": 0.0, "max": 0}},
                {"not_within": {"layer": "floodplain"}},
            ],
            "score": [
                {"attr_value": {"field": "acres", "prefer": "high", "weight": 0.5}},
                {"proximity": {"to": "highways", "prefer": "near", "weight": 0.5}},
            ],
        },
    },
]

_BY_KEY = {p["key"]: p for p in PRESETS}


def get(key: str) -> dict:
    return _BY_KEY[key]


def missing_data(preset: dict, columns, layers) -> list[str]:
    """Which of a preset's needs aren't loaded yet (columns not present, layers absent)."""
    have = set(columns) | set(layers)
    return [n for n in preset["needs"] if n not in have]
