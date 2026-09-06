"""
SGW Hurricane Risk & Crew Coordination - lightweight prototype.

Scores SGW's grid assets against Hurricane Helene's track and recommends crew assignments for the highest-risk ones. 
Everything here is a recommendation, nothing gets auto-approved.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.generate_data import main as generate_data_main  # noqa: E402
from model.train_risk_model import main as train_model_main  # noqa: E402
from optimisation import recommend_assignments  # noqa: E402
from risk_scoring import load_model, score_assets  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent / "model" / "risk_model.pkl"

st.set_page_config(page_title="SGW Hurricane Risk & Crew Coordination", layout="wide")


@st.cache_resource(show_spinner="Preparing demo data and training the risk model (first run only)...")
def bootstrap():
    if not (DATA_DIR / "assets.csv").exists():
        generate_data_main()
    if not MODEL_PATH.exists():
        train_model_main()
    return True


@st.cache_data
def load_data():
    assets = pd.read_csv(DATA_DIR / "assets.csv")
    crews = pd.read_csv(DATA_DIR / "crews.csv")
    track = pd.read_csv(DATA_DIR / "helene_track.csv")
    return assets, crews, track


def category_color(cat):
    return {
        0: [120, 120, 200],
        1: [255, 237, 160],
        2: [254, 178, 76],
        3: [253, 141, 60],
        4: [227, 26, 28],
        5: [128, 0, 38],
    }.get(int(cat), [150, 150, 150])


def risk_color(risk, max_risk):
    frac = 0 if max_risk == 0 else risk / max_risk
    return [int(255 * frac), int(180 * (1 - frac)), 60, 200]


bootstrap()
assets_df, crews_df, full_track_df = load_data()
model = load_model()

st.title("SGW Hurricane Risk & Crew Coordination")
st.caption(
    "Prototype for the AECOM AI Solution Engineer case. Scenario: Hurricane Helene "
    "(2024)'s real track, replayed against a fictional SGW electric grid territory."
)

with st.sidebar:
    st.header("Forecast Advisory")
    advisory_idx = st.slider(
        "How much of the storm's track is known so far",
        min_value=1,
        max_value=len(full_track_df),
        value=len(full_track_df),
        help="Mirrors the PRD's ~6-hourly advisory refresh: earlier advisories "
             "know less about the storm's eventual path, so risk scores sharpen "
             "as later advisories come in.",
    )
    current_point = full_track_df.iloc[advisory_idx - 1]
    st.metric("Latest known position", current_point["label"])
    st.metric("Category at that point", int(current_point["category"]))

    st.divider()
    with st.expander("About this prototype"):
        st.markdown(
            "- All SGW data (assets, crews, maintenance history) is fictional and generated for this demo.\n"
            "- Hurricane Helene's landfall time/location/intensity and general inland path are real "
            "(NHC-documented); waypoints between them are interpolated for this prototype.\n"
            "- The risk model is a gradient-boosted-trees classifier trained on synthetic historical "
            "storm data with a designed (not random) relationship between hazard/asset features and outcome.\n"
            "- Everything shown here is a **recommendation**. Nothing is auto-dispatched or de-energised; "
            "a human approves every action, per the PRD's governance section."
        )

track_points = full_track_df.iloc[:advisory_idx].to_dict("records")
ranked = score_assets(assets_df, track_points, model)

tab1, tab2, tab3 = st.tabs(["Storm Overview", "Risk Ranking", "Crew Assignment"])

# ---------------------------------------------------------------------------
with tab1:
    st.subheader("Hurricane Helene: track known so far")
    known_track = full_track_df.iloc[:advisory_idx].copy()
    known_track["color"] = known_track["category"].apply(category_color)

    path_layer = pdk.Layer(
        "PathLayer",
        data=[{"path": known_track[["lon", "lat"]].values.tolist()}],
        get_path="path",
        get_color=[80, 80, 200],
        width_min_pixels=3,
    )
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=known_track,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius=15000,
        pickable=True,
    )
    asset_layer = pdk.Layer(
        "ScatterplotLayer",
        data=assets_df,
        get_position="[lon, lat]",
        get_fill_color=[40, 40, 40, 120],
        get_radius=4000,
    )
    view_state = pdk.ViewState(latitude=32.5, longitude=-83.5, zoom=5.3)
    st.pydeck_chart(pdk.Deck(
        layers=[asset_layer, path_layer, point_layer],
        initial_view_state=view_state,
        tooltip={"text": "{label}\nCategory {category}, {max_wind_mph} mph"},
        map_style=None,
    ))
    st.caption("Blue/yellow/orange/red dots: storm position and category at each known advisory point. "
               "Small dark dots: SGW grid assets.")

    st.subheader("Track detail")
    st.dataframe(
        known_track[["datetime", "label", "category", "max_wind_mph"]],
        hide_index=True, width='stretch',
    )

# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Assets ranked by composite risk")
    st.caption("composite risk = probability of failure x consequence (customers served x criticality)")

    max_risk = ranked["composite_risk"].max()
    ranked_map = ranked.copy()
    ranked_map["color"] = ranked_map["composite_risk"].apply(lambda r: risk_color(r, max_risk))
    ranked_map["radius"] = 3000 + ranked_map["composite_risk"] / max_risk * 12000

    risk_layer = pdk.Layer(
        "ScatterplotLayer",
        data=ranked_map,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius="radius",
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[risk_layer],
        initial_view_state=pdk.ViewState(latitude=32.5, longitude=-83.5, zoom=5.3),
        tooltip={"text": "{name}\nRisk: {composite_risk}"},
        map_style=None,
    ))

    top_n = st.slider("Show top N assets", 5, len(ranked), 15)
    display_cols = [
        "asset_id", "name", "asset_type", "service_area", "customers_served",
        "criticality_flag", "probability_of_failure", "composite_risk",
    ]
    st.dataframe(
        ranked[display_cols].head(top_n).style.format({
            "probability_of_failure": "{:.1%}",
            "composite_risk": "{:.3f}",
        }),
        hide_index=True, width='stretch',
    )

    st.subheader("Explain a specific asset's score")
    selected = st.selectbox("Asset", ranked["asset_id"] + " -- " + ranked["name"])
    sel_id = selected.split(" -- ")[0]
    sel_row = ranked[ranked["asset_id"] == sel_id].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Probability of failure", f"{sel_row['probability_of_failure']:.1%}")
    c2.metric("Consequence score", f"{sel_row['consequence_score']:.2f}")
    c3.metric("Composite risk", f"{sel_row['composite_risk']:.3f}")
    st.markdown("**Top contributing factors:** " + ", ".join(sel_row["top_factors"]))

# ---------------------------------------------------------------------------
with tab3:
    st.subheader("Recommended crew assignments")
    st.caption(
        f"{crews_df['available'].sum()} of {len(crews_df)} crews currently available. "
        "Assignment is optimised (Hungarian algorithm) to minimise total travel distance "
        "to the highest-risk assets -- it does not attempt to cover every at-risk asset."
    )

    assignments = recommend_assignments(ranked, crews_df)

    if "approval_state" not in st.session_state:
        st.session_state.approval_state = {}

    for _, row in assignments.iterrows():
        key = f"{row['crew_id']}_{row['asset_id']}"
        state = st.session_state.approval_state.get(key, "Pending Approval")
        cols = st.columns([2, 3, 2, 2, 2])
        cols[0].markdown(f"**{row['crew_id']}**  \n{row['crew_base']}")
        cols[1].markdown(f"**{row['asset_name']}**  \nRisk: {row['composite_risk']:.3f}")
        cols[2].markdown(f"{row['travel_miles']} mi")
        cols[3].markdown(f"Status: **{state}**")
        b1, b2 = cols[4].columns(2)
        if b1.button("Approve", key=f"approve_{key}"):
            st.session_state.approval_state[key] = "Approved"
            st.rerun()
        if b2.button("Reject", key=f"reject_{key}"):
            st.session_state.approval_state[key] = "Rejected"
            st.rerun()

    st.divider()
    st.subheader("Crew bases and recommended assignments")
    lines = []
    for _, row in assignments.iterrows():
        crew = crews_df[crews_df["crew_id"] == row["crew_id"]].iloc[0]
        asset = ranked[ranked["asset_id"] == row["asset_id"]].iloc[0]
        lines.append({
            "source": [crew["base_lon"], crew["base_lat"]],
            "target": [asset["lon"], asset["lat"]],
        })
    arc_layer = pdk.Layer(
        "ArcLayer",
        data=lines,
        get_source_position="source",
        get_target_position="target",
        get_source_color=[0, 128, 200],
        get_target_color=[227, 26, 28],
        get_width=3,
    )
    crew_layer = pdk.Layer(
        "ScatterplotLayer",
        data=crews_df,
        get_position="[base_lon, base_lat]",
        get_fill_color=[0, 128, 200, 200],
        get_radius=6000,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[arc_layer, crew_layer],
        initial_view_state=pdk.ViewState(latitude=32.5, longitude=-83.5, zoom=5.3),
        map_style=None,
    ))
