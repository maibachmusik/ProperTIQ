"""ProperTIQ — no-code strategy builder (Streamlit).

Build, run, and export a site-suitability strategy without writing code. Every
block and every tooltip is sourced from ``propertiq.registry`` so what you see
matches what the engine does.

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

# Work both as a package module (`import app.strategy_builder`, used by tests) and
# as a top-level script (`streamlit run app/strategy_builder.py`, where there is
# no parent package and the script's own directory is on sys.path).
try:
    from app import _logic
except ImportError:  # pragma: no cover - the `streamlit run` path
    import _logic  # type: ignore[no-redef]


# --------------------------------------------------------------------------- #
# Data loading helpers
# --------------------------------------------------------------------------- #
def _read_geo(uploaded: Any) -> Any:
    """Read an uploaded GeoJSON/GeoParquet file into a GeoDataFrame."""
    import geopandas as gpd

    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".parquet"):
        return gpd.read_parquet(io.BytesIO(data))
    return gpd.read_file(io.BytesIO(data))


def _render_param(st, spec: dict[str, Any], value: Any, key: str) -> Any:
    """Render one parameter widget, always wiring its registry tooltip into ``help``."""
    kind, label, help_ = spec["kind"], spec["label"], spec["help"]
    if kind in ("number", "integer"):
        step = 1.0 if kind == "number" else 1
        val = 0 if value is None else value
        return st.number_input(label, value=val, help=help_, key=key, step=step)
    if kind == "bool":
        return st.checkbox(label, value=bool(value), help=help_, key=key)
    if kind == "select":
        opts = spec["options"] or []
        idx = opts.index(value) if value in opts else 0
        return st.selectbox(label, opts, index=idx, help=help_, key=key)
    if kind == "multiselect":
        return st.multiselect(
            label, spec["options"] or [], default=value or [], help=help_, key=key
        )
    if kind in ("layer", "field"):
        opts = spec["options"] or []
        if not opts:
            st.warning(f"'{label}': add data first to choose a value.")
            return value
        idx = opts.index(value) if value in opts else 0
        return st.selectbox(label, opts, index=idx, help=help_, key=key)
    return st.text_input(label, value="" if value is None else str(value), help=help_, key=key)


def _block_editor(st, section: str, blocks: list[dict], layer_names, field_names) -> list[dict]:
    """Render the add/edit UI for one section (filters or scoring); return new state."""
    specs = registry.filters() if section == "filters" else registry.criteria()
    choices = {b.label: b.key for b in specs}

    cols = st.columns([3, 1])
    pick = cols[0].selectbox(
        f"Add a {'filter' if section == 'filters' else 'scoring criterion'}",
        list(choices),
        key=f"add_{section}",
        help=next(
            (b.description for b in specs if b.label == st.session_state.get(f"add_{section}")), ""
        ),
    )
    if cols[1].button("Add", key=f"addbtn_{section}"):
        blocks.append(_logic.new_block_state(choices[pick]))

    kept: list[dict] = []
    for i, block in enumerate(blocks):
        spec = registry.get(block["key"])
        with st.expander(f"{spec.label}", expanded=True):
            st.caption(spec.description)  # the block's own plain-language tooltip
            for p in spec.params:
                wspec = _logic.param_widget_spec(
                    p, layer_names=layer_names, field_names=field_names
                )
                block["params"][p.name] = _render_param(
                    st, wspec, block["params"].get(p.name), key=f"{section}_{i}_{p.name}"
                )
            if not st.button("Remove", key=f"rm_{section}_{i}"):
                kept.append(block)
    return kept


def main() -> None:  # pragma: no cover - exercised via `streamlit run`, not unit tests
    import streamlit as st
    import yaml

    st.set_page_config(page_title="ProperTIQ — Strategy Builder", layout="wide")
    st.title("ProperTIQ — Strategy Builder")
    st.caption(
        "Score and rank parcels for any purpose. No code — every option is explained inline."
    )

    ss = st.session_state
    if "state" not in ss:
        ss.state = _logic.new_state("my_strategy")
    if "layers" not in ss:
        ss.layers = {}

    # --- Sidebar: data ------------------------------------------------------
    with st.sidebar:
        st.header("1 · Data")
        pf = st.file_uploader("Parcels (GeoJSON / GeoParquet)", type=["geojson", "json", "parquet"])
        if pf is not None:
            ss.parcels = _read_geo(pf)
            st.success(f"{len(ss.parcels):,} parcels loaded.")

        st.subheader("Layers (optional)")
        st.caption("Roads, competitors, floodplains… referenced by Proximity/Gap/Exclude rules.")
        lname = st.text_input("Layer name", placeholder="highways")
        lf = st.file_uploader("Layer file", type=["geojson", "json", "parquet"], key="layerfile")
        if st.button("Add layer") and lname and lf is not None:
            ss.layers[lname] = _read_geo(lf)
        if ss.layers:
            st.write("Loaded layers:", ", ".join(ss.layers))

        st.divider()
        up = st.file_uploader("Load a saved strategy (YAML)", type=["yaml", "yml"], key="loadstrat")
        if up is not None and st.button("Load strategy"):
            ss.state = _logic.config_to_session(yaml.safe_load(up.read()))
            st.success("Strategy loaded.")

    parcels = ss.get("parcels")
    field_names = list(parcels.columns.drop(parcels.geometry.name)) if parcels is not None else []
    layer_names = list(ss.layers)

    # --- Builder ------------------------------------------------------------
    ss.state["name"] = st.text_input("Strategy name", ss.state.get("name", "my_strategy"))

    st.header("2 · Hard filters")
    st.caption("Pass/fail rules. Parcels that fail any filter are dropped.")
    ss.state["filters"] = _block_editor(
        st, "filters", ss.state["filters"], layer_names, field_names
    )

    st.header("3 · Scoring criteria")
    st.caption("Weighted signals. Each scores 0–100; weights auto-balance to 100%.")
    ss.state["score"] = _block_editor(st, "score", ss.state["score"], layer_names, field_names)

    # --- Run ----------------------------------------------------------------
    st.header("4 · Run")
    config = _logic.session_to_config(ss.state)
    with st.expander("Strategy as config (YAML)"):
        st.code(yaml.safe_dump(config, sort_keys=False), language="yaml")

    if st.button("▶ Run strategy", type="primary"):
        if parcels is None:
            st.error("Upload a parcels file first.")
        elif not ss.state["score"]:
            st.error("Add at least one scoring criterion.")
        else:
            try:
                from propertiq import from_config

                result = from_config(config, layers=ss.layers).run(parcels)
                ss.result = result
            except Exception as exc:  # surface engine errors readably
                st.error(f"{type(exc).__name__}: {exc}")

    # --- Results ------------------------------------------------------------
    result = ss.get("result")
    if result is not None and len(result.parcels):
        st.header("5 · Results")
        n = st.slider("Show top N", 1, min(200, len(result.parcels)), min(20, len(result.parcels)))
        top = result.top(n)
        show_cols = [
            c for c in top.columns if c != top.geometry.name and not c.startswith("signal__")
        ]
        st.dataframe(top[show_cols], use_container_width=True)

        st.subheader("Why each scored what it did")
        st.dataframe(result.explain().head(n), use_container_width=True)

        try:
            import folium
            from streamlit_folium import st_folium

            wgs = top.to_crs(4326)
            center = [wgs.geometry.centroid.y.mean(), wgs.geometry.centroid.x.mean()]
            fmap = folium.Map(location=center, zoom_start=12)
            folium.GeoJson(
                wgs.assign(score=wgs["score"].round(1))[["score", wgs.geometry.name]],
                tooltip=folium.GeoJsonTooltip(fields=["score"]),
            ).add_to(fmap)
            st_folium(fmap, width=900, height=480)
        except Exception as exc:
            st.info(f"Map unavailable: {exc}")

        # --- Export ---------------------------------------------------------
        st.subheader("Export")
        c1, c2 = st.columns(2)
        gj = io.BytesIO()
        result.parcels.to_crs(4326).assign(
            score_breakdown=result.parcels["score_breakdown"].apply(lambda d: str(d))
        ).to_file(gj, driver="GeoJSON")
        c1.download_button("Candidates (GeoJSON)", gj.getvalue(), f"{ss.state['name']}.geojson")
        c2.download_button(
            "Strategy (YAML)", yaml.safe_dump(config, sort_keys=False), f"{ss.state['name']}.yaml"
        )


if __name__ == "__main__":
    main()
