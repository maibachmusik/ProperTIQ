"""ProperTIQ — no-code strategy builder (Streamlit).

Build, run, and export a site-suitability strategy without writing code. Pick a
search area (ZIP or address + radius), bring or auto-load parcels, compose filters
and weighted criteria from a labeled list (every option explained inline by the
library's registry), tune the weights, and run.

Run it::

    pip install "propertiq[app]"
    streamlit run app/strategy_builder.py

All UI lives under ``main()`` so importing this module has no side effects
(spec 003, SC-A4).
"""

from __future__ import annotations

import io
from typing import Any

from propertiq import registry

# Work both as a package module (tests) and as a `streamlit run` script.
try:
    from app import _aoi, _enrich, _logic, presets as _presets
except ImportError:  # pragma: no cover - the `streamlit run` path
    import _aoi  # type: ignore[no-redef]
    import _enrich  # type: ignore[no-redef]
    import _logic  # type: ignore[no-redef]
    import presets as _presets  # type: ignore[no-redef]


def _load_preset(ss, preset: dict) -> None:
    """Populate the builder from a preset config, assigning fresh block ids."""
    state = _logic.config_to_session(preset["config"])
    for section in ("filters", "score"):
        for block in state[section]:
            block["id"] = _next_id(ss)
    ss.state = state
    ss.result = None


# Verified Colorado Front Range county parcel portals (for the bring-your-own guide).
_CO_PORTALS = [
    ("Larimer", "https://www.larimer.gov/it/gis", "GIS Digital Data page (no one-click hub)"),
    ("Weld", "https://gishub.weldgov.com", "search 'parcels' → Download"),
    (
        "Boulder",
        "https://opendata-bouldercounty.hub.arcgis.com/datasets/parcels",
        "Download → GeoJSON/Shapefile",
    ),
    (
        "Adams",
        "https://data-adcogov.opendata.arcgis.com/datasets/ADCOGOV::parcels/about",
        "Download → GeoJSON/Shapefile",
    ),
    ("Denver", "https://opendata-geospatialdenver.hub.arcgis.com/", "search 'parcels' → Download"),
    (
        "Jefferson",
        "https://data-jeffersoncounty.opendata.arcgis.com/datasets/jeffersoncounty::parcel/explore",
        "Download → GeoJSON/Shapefile",
    ),
    ("El Paso", "https://opendata-elpasoco.hub.arcgis.com/", "search 'parcels' → Download"),
]
_CO_STATEWIDE = "https://geodata.colorado.gov/datasets/colorado-public-parcels/about"


# --------------------------------------------------------------------------- #
# Session-state callbacks (mutate state cleanly before the rerun)
# --------------------------------------------------------------------------- #
def _next_id(ss) -> int:
    ss._next_id += 1
    return ss._next_id


def _add_block(ss, section: str) -> None:
    key = ss[f"pick_{section}"]  # the picker's value is the block key
    ss.state[section].append({"id": _next_id(ss), **_logic.new_block_state(key)})


def _remove_block(ss, section: str, bid: int) -> None:
    ss.state[section] = [b for b in ss.state[section] if b["id"] != bid]


# --------------------------------------------------------------------------- #
# Widget rendering (registry-driven; tooltips always wired)
# --------------------------------------------------------------------------- #
def _render_param(st, wspec: dict[str, Any], block: dict, section: str) -> Any:
    name = wspec["name"]
    key = f"w_{section}_{block['id']}_{name}"
    kind, label, help_ = wspec["kind"], wspec["label"], wspec["help"]
    options = wspec.get("options") or []
    cur = block["params"].get(name, wspec["default"])

    if name == "weight":
        v = float(cur) if cur is not None else 1.0
        return st.slider(
            label, 0.0, 1.0, value=min(max(v, 0.0), 1.0), step=0.05, key=key, help=help_
        )
    if kind in ("number", "integer"):
        if wspec["required"]:
            return st.number_input(
                label, value=float(cur) if cur is not None else 0.0, key=key, help=help_
            )
        # optional numeric (e.g. AttrRange min/max) — allow blank
        return st.number_input(
            label, value=float(cur) if cur is not None else None, key=key, help=help_
        )
    if kind == "bool":
        return st.checkbox(label, value=bool(cur), key=key, help=help_)
    if kind == "multiselect":
        default = [v for v in (cur or []) if v in options]
        return st.multiselect(label, options, default=default, key=key, help=help_)
    if kind in ("select", "layer", "field"):
        if not options:
            st.info(f"'{label}': load data / add a layer first.")
            return cur
        idx = options.index(cur) if cur in options else 0
        return st.selectbox(label, options, index=idx, key=key, help=help_)
    return st.text_input(label, value="" if cur is None else str(cur), key=key, help=help_)


def _section(st, ss, section: str, parcels, layer_names, field_names) -> None:
    specs = registry.filters() if section == "filters" else registry.criteria()
    order = {c: i for i, c in enumerate(registry.categories())}
    specs = sorted(specs, key=lambda b: (order.get(b.category, 99), b.label))
    keys = [b.key for b in specs]

    def fmt(k: str) -> str:  # group visually: "Site & terrain · Cardinal direction facing"
        b = registry.get(k)
        return f"{b.category} · {b.label}"

    picked = ss.get(f"pick_{section}", keys[0])
    c1, c2 = st.columns([4, 1])
    c1.selectbox(
        "Add a filter" if section == "filters" else "Add a scoring criterion",
        keys,
        format_func=fmt,
        key=f"pick_{section}",
        help=registry.get(picked).description,
    )
    c2.button("➕ Add", key=f"addbtn_{section}", on_click=_add_block, args=(ss, section))

    for block in ss.state[section]:
        spec = registry.get(block["key"])
        with st.expander(spec.label, expanded=True):
            st.caption(spec.description)
            for p in spec.params:
                wspec = _logic.param_widget_spec(
                    p, layer_names=layer_names, field_names=field_names
                )
                # The "allowed values" multiselect populates from the chosen field's values.
                if p.name == "values":
                    fld = block["params"].get("field")
                    if fld and fld in getattr(parcels, "columns", []):
                        vals = sorted(str(v) for v in parcels[fld].dropna().unique())
                        wspec["options"] = vals[:1000]
                block["params"][p.name] = _render_param(st, wspec, block, section)
            st.button(
                "🗑 Remove",
                key=f"rm_{section}_{block['id']}",
                on_click=_remove_block,
                args=(ss, section, block["id"]),
            )


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def _load_area(st, ss, mode: str, method: str, query: str, radius: float, upload) -> None:
    if method == "ZIP code":
        lat, lon, label = _aoi.geocode_zip(query)
    else:
        lat, lon, label = _aoi.geocode_address(query)
    circle, bbox = _aoi.aoi_from_point(lat, lon, radius)

    if mode.startswith("Front Range"):
        parcels = _aoi.fetch_front_range_parcels(bbox)
        if len(parcels) == 0:
            st.warning(
                f"No demo parcels at {label} — the demo covers the Colorado Front "
                "Range (Larimer + Weld counties; try 80538 Loveland or 80631 "
                "Greeley). Switch to 'Bring my own' to upload parcels for anywhere."
            )
            return
    else:
        if upload is None:
            st.error("Upload a parcels file first (see the portal links above).")
            return
        parcels = _aoi.read_upload(upload.name, upload.read())
        if parcels.crs is None:
            parcels = parcels.set_crs(4326)
        parcels = _aoi.clip_to_aoi(parcels, circle)
        if "acres" not in parcels.columns:
            parcels["acres"] = parcels.to_crs(5070).area / 4046.8564224

    layers = _aoi.fetch_context(bbox)  # highways, floodplain
    try:
        # Fast open data: terrain (3DEP slope/aspect), canopy (LANDFIRE), soils
        # (SSURGO). These power Facing/slope/canopy/soil rules immediately. OSM
        # structures/layers load on demand (the first OSM pull is slow).
        parcels = _enrich.add_terrain(parcels)
    except Exception as exc:
        st.info(f"Terrain data unavailable ({exc}); other rules still work.")
    try:
        parcels, land_layers = _enrich.add_land(parcels, bbox)
        layers.update(land_layers)
    except Exception:
        pass

    ss.parcels = parcels
    ss.layers = layers
    ss.aoi = {"label": label, "lat": lat, "lon": lon, "radius": radius, "bbox": bbox}
    ss.result = None
    added = [
        c
        for c in ("slope_deg", "aspect_deg", "canopy_pct", "soil_drainage")
        if c in parcels.columns
    ]
    st.success(
        f"Loaded {len(parcels):,} parcels near {label} ({radius} mi). "
        f"Layers: {', '.join(layers) or 'none'}."
        + (f" Site data: {', '.join(added)}." if added else "")
    )


def main() -> None:  # pragma: no cover - exercised via streamlit, not unit tests
    import streamlit as st
    import yaml

    st.set_page_config(page_title="ProperTIQ — Strategy Builder", layout="wide")
    ss = st.session_state
    ss.setdefault("state", _logic.new_state("my_strategy"))
    ss.setdefault("layers", {})
    ss.setdefault("_next_id", 0)

    st.title("ProperTIQ — Strategy Builder")
    st.caption(
        "Find land that fits your rules — score & rank parcels, no code. Every option is explained inline."
    )

    # ---------------- Step 1 · Area + data --------------------------------- #
    st.header("1 · Search area & parcels")
    mode = st.radio(
        "Parcel data",
        ["Front Range demo (real parcels)", "Bring my own (upload)"],
        horizontal=True,
        help="The demo auto-loads real Colorado Front Range parcels. Otherwise upload your own.",
    )
    if mode.startswith("Bring"):
        with st.expander("Where do I get parcel data? (county / state GIS portals)"):
            st.markdown(
                "Parcels come from your **county or state GIS open-data portal** — "
                "download GeoJSON or a zipped Shapefile, then upload it here.\n\n"
                + "\n".join(f"- **{c}** — [{u}]({u}) · {note}" for c, u, note in _CO_PORTALS)
                + f"\n- **Colorado statewide** — [Colorado Public Parcels]({_CO_STATEWIDE})\n\n"
                "_Most counties: search 'parcels' → Download → GeoJSON/Shapefile._"
            )
        upload = st.file_uploader(
            "Parcels (GeoJSON / GeoParquet / zipped Shapefile)",
            type=["geojson", "json", "parquet", "zip"],
        )
    else:
        upload = None

    c1, c2, c3 = st.columns([2, 3, 2])
    method = c1.radio("Find area by", ["ZIP code", "Address / place"])
    query = c2.text_input(
        "ZIP code" if method == "ZIP code" else "Address or place",
        value="80538" if method == "ZIP code" else "",
        placeholder="80538" if method == "ZIP code" else "Loveland, CO",
    )
    radius = c3.slider("Search radius (miles)", 0.5, 15.0, 1.5, step=0.5)
    if st.button("📍 Load area", type="primary"):
        if not query.strip():
            st.error("Enter a ZIP or address.")
        else:
            with st.spinner("Geocoding and fetching open data…"):
                try:
                    _load_area(st, ss, mode, method, query, radius, upload)
                except Exception as exc:
                    st.error(f"{type(exc).__name__}: {exc}")

    parcels = ss.get("parcels")
    if parcels is None:
        st.info("Pick a search area and click **Load area** to begin.")
        return
    st.caption(f"📦 {len(parcels):,} parcels · layers: {', '.join(ss.layers) or 'none'}")

    # On-demand: OSM structures + site layers (buildings, water, power, roads).
    # Kept off the fast path because the first OSM pull can take a while.
    if "structures" not in parcels.columns:
        if st.button("🏗 Add structures & site layers (buildings, water, power, roads)"):
            with st.spinner("Fetching OpenStreetMap structures & site layers…"):
                try:
                    site_layers = _enrich.fetch_site_layers(ss.aoi["bbox"])
                    ss.layers.update(site_layers)
                    if "buildings" in site_layers:
                        ss.parcels = _enrich.add_structures(parcels, site_layers["buildings"])
                    st.success(
                        f"Added: {', '.join(site_layers) or 'none'} (+ a `structures` count)."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"{type(exc).__name__}: {exc}")
    else:
        st.caption(f"🏗 structures loaded (max {int(parcels['structures'].max())} per parcel).")
    parcels = ss.get("parcels")

    # Optional: pull a competitor / POI layer from OpenStreetMap for the AOI.
    with st.expander("Add a competitor / POI layer from OpenStreetMap"):
        oc1, oc2, oc3, oc4 = st.columns([2, 2, 2, 1])
        lname = oc1.text_input("Layer name", placeholder="competitors", key="osm_name")
        tkey = oc2.text_input("OSM tag key", value="amenity", key="osm_key")
        tval = oc3.text_input("OSM tag value", placeholder="car_wash", key="osm_val")
        if oc4.button("Fetch") and lname and tkey and tval:
            try:
                gdf = _aoi.fetch_osm_points(ss.aoi["bbox"], tkey, tval)
                ss.layers[lname] = gdf
                st.success(f"Added '{lname}' ({len(gdf)} features).")
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")

    field_names = [c for c in parcels.columns if c != parcels.geometry.name]
    layer_names = list(ss.layers)

    # Presets: one click populates the builder with a ready-made strategy.
    with st.expander("⚡ Start from a preset strategy"):
        labels = {p["label"]: p for p in _presets.PRESETS}
        pick = st.selectbox("Preset", list(labels), key="preset_pick")
        chosen = labels[pick]
        st.caption(chosen["desc"])
        missing = _presets.missing_data(chosen, field_names, layer_names)
        if missing:
            st.caption(
                f"ⓘ Needs data not loaded yet: {', '.join(missing)} — load it above "
                "(the preset still loads; fix any unset dropdowns)."
            )
        if st.button("Load this preset", key="load_preset"):
            _load_preset(ss, chosen)
            st.success(f"Loaded '{chosen['label']}'. Tune the weights below and run.")
            st.rerun()

    # ---------------- Step 2 · Strategy ------------------------------------ #
    ss.state["name"] = st.text_input("Strategy name", ss.state.get("name", "my_strategy"))
    st.header("2 · Hard filters")
    st.caption("Pass/fail rules. Parcels that fail any filter are dropped.")
    _section(st, ss, "filters", parcels, layer_names, field_names)

    st.header("3 · Scoring criteria")
    st.caption("Weighted signals. Each scores 0–100; the weights below auto-balance to 100%.")
    _section(st, ss, "score", parcels, layer_names, field_names)

    weights = _logic.normalized_weights(ss.state)
    if weights:
        st.write("**Effective weights**")
        for nm, w in weights.items():
            st.write(f"{nm} — {w:.0%}")
            st.progress(w)

    # ---------------- Step 3 · Run ----------------------------------------- #
    st.header("4 · Run")
    config = _logic.session_to_config(ss.state)
    with st.expander("Strategy as config (YAML)"):
        st.code(yaml.safe_dump(config, sort_keys=False), language="yaml")

    if st.button("▶ Run strategy", type="primary"):
        if not ss.state["score"]:
            st.error("Add at least one scoring criterion.")
        else:
            try:
                from propertiq import from_config

                ss.result = from_config(config, layers=ss.layers).run(parcels)
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")

    result = ss.get("result")
    if result is not None and len(result.parcels):
        st.header("5 · Results")
        st.success(f"{len(result.parcels):,} candidate parcels, ranked.")
        n = st.slider("Show top N", 1, min(200, len(result.parcels)), min(20, len(result.parcels)))
        top = result.top(n)
        cols = [
            c
            for c in top.columns
            if c != top.geometry.name and not c.startswith("signal__") and c != "score_breakdown"
        ]
        st.dataframe(top[cols], width="stretch")

        st.subheader("Why each scored what it did")
        st.dataframe(result.explain().head(n), width="stretch")

        try:
            from streamlit_folium import st_folium

            st_folium(result.to_map(n=n), width=900, height=480, returned_objects=[])
        except Exception as exc:
            st.info(f"Map unavailable: {exc}")

        st.subheader("Export")
        e1, e2 = st.columns(2)
        gj = io.BytesIO()
        result.parcels.to_crs(4326).assign(
            score_breakdown=result.parcels["score_breakdown"].apply(str)
        ).to_file(gj, driver="GeoJSON")
        e1.download_button("Candidates (GeoJSON)", gj.getvalue(), f"{ss.state['name']}.geojson")
        e2.download_button(
            "Strategy (YAML)", yaml.safe_dump(config, sort_keys=False), f"{ss.state['name']}.yaml"
        )
    elif result is not None:
        st.warning("No parcels survived the filters — loosen a filter and run again.")


if __name__ == "__main__":
    main()
