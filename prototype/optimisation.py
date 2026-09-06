"""Crew-to-asset assignment via the Hungarian algorithm (scipy's linear_sum_assignment)."""

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from risk_scoring import haversine_miles


def recommend_assignments(ranked_assets_df, crews_df):
    """
    Match each available crew to one of the top-N highest-risk assets (N = number of crews we have), minimising total travel distance.
    Only covers the top N on purpose (if there are more high-risk assets than crews, the point is choosing which ones get covered first).
    """
    available = crews_df[crews_df["available"]].reset_index(drop=True)
    n_crews = len(available)
    if n_crews == 0:
        return pd.DataFrame()

    top_assets = ranked_assets_df.head(n_crews).reset_index(drop=True)

    cost = np.zeros((n_crews, len(top_assets)))
    for i, crew in available.iterrows():
        for j, asset in top_assets.iterrows():
            cost[i, j] = haversine_miles(crew["base_lat"], crew["base_lon"], asset["lat"], asset["lon"])

    crew_idx, asset_idx = linear_sum_assignment(cost)

    rows = []
    for c_i, a_i in zip(crew_idx, asset_idx):
        crew = available.iloc[c_i]
        asset = top_assets.iloc[a_i]
        rows.append({
            "crew_id": crew["crew_id"],
            "crew_base": crew["base_name"],
            "asset_id": asset["asset_id"],
            "asset_name": asset["name"],
            "composite_risk": asset["composite_risk"],
            "travel_miles": round(cost[c_i, a_i], 1),
            "status": "Pending Approval",
        })
    return pd.DataFrame(rows).sort_values("composite_risk", ascending=False).reset_index(drop=True)
