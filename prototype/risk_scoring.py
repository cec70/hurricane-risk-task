"""
Wind-field model, feature engineering, and the risk model itself.

Shared by data/generate_data.py (builds training examples) and app.py (scores the live Helene scenario) so both use the exact same pipeline.
"""

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

MODEL_PATH = Path(__file__).parent / "model" / "risk_model.pkl"

FEATURE_COLUMNS = [
    "max_wind_experienced_mph",
    "storm_surge_exposure",
    "age_years",
    "years_since_inspection",
    "prior_outage_count",
    "vegetation_density",
    "flood_zone",
    "distance_to_coast_km",
]


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in miles."""
    r = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def radius_of_max_winds(category):
    # Stronger storms tend to have a tighter wind core.
    if category >= 4:
        return 25.0
    if category >= 2:
        return 35.0
    return 45.0


def wind_speed_at_distance(vmax_mph, category, distance_miles):
    # Simplified Rankine vortex: winds ramp up to the radius of max winds, then decay outward. Using a gentle decay exponent (0.5) on purpose 
    # Helene did real wind damage well inland (Asheville included), and a steeper falloff would understate that.
    rmw = radius_of_max_winds(category)
    if distance_miles <= rmw:
        return vmax_mph * (distance_miles / rmw)
    return vmax_mph * (rmw / distance_miles) ** 0.5


def max_wind_experienced(asset_lat, asset_lon, track_points):
    """Strongest wind an asset would feel as the storm passes closest to it."""
    best = 0.0
    for pt in track_points:
        dist = haversine_miles(asset_lat, asset_lon, pt["lat"], pt["lon"])
        w = wind_speed_at_distance(pt["max_wind_mph"], pt["category"], dist)
        best = max(best, w)
    return best


def storm_surge_exposure(asset_lat, asset_lon, distance_to_coast_km, track_points):
    """Rough surge proxy, 0-1: only matters for coastal assets near a strong storm."""
    if distance_to_coast_km > 40:
        return 0.0
    peak_category_nearby = 0
    for pt in track_points:
        dist_miles = haversine_miles(asset_lat, asset_lon, pt["lat"], pt["lon"])
        if dist_miles <= 75:
            peak_category_nearby = max(peak_category_nearby, pt["category"])
    if peak_category_nearby == 0:
        return 0.0
    coastal_factor = max(0.0, 1 - distance_to_coast_km / 40)
    return coastal_factor * (peak_category_nearby / 5)


def build_features(asset_row, track_points, as_of_year=2024):
    wind = max_wind_experienced(asset_row["lat"], asset_row["lon"], track_points)
    surge = storm_surge_exposure(
        asset_row["lat"], asset_row["lon"], asset_row["distance_to_coast_km"], track_points
    )
    return {
        "max_wind_experienced_mph": wind,
        "storm_surge_exposure": surge,
        "age_years": asset_row["age_years"],
        "years_since_inspection": as_of_year - asset_row["last_inspection_year"],
        "prior_outage_count": asset_row["prior_outage_count"],
        "vegetation_density": asset_row["vegetation_density"],
        "flood_zone": int(asset_row["flood_zone"]),
        "distance_to_coast_km": asset_row["distance_to_coast_km"],
    }


def train_model(training_df):
    X = training_df[FEATURE_COLUMNS]
    y = training_df["failed"]
    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X, y)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    return joblib.load(MODEL_PATH)


def score_assets(assets_df, track_points, model, as_of_year=2024):
    """Score every asset against a storm track: probability, consequence, composite risk."""
    feature_rows = [build_features(row, track_points, as_of_year) for _, row in assets_df.iterrows()]
    features_df = pd.DataFrame(feature_rows)[FEATURE_COLUMNS]

    probabilities = model.predict_proba(features_df)[:, 1]

    consequence = assets_df["customers_served"] * assets_df["criticality_multiplier"]
    consequence_norm = consequence / consequence.max()

    result = assets_df.copy()
    result["probability_of_failure"] = probabilities
    result["consequence_score"] = consequence_norm
    result["composite_risk"] = result["probability_of_failure"] * result["consequence_score"]
    for col in FEATURE_COLUMNS:
        result[col] = features_df[col].values

    # Explainability: for each asset, which features are both important to
    # the model AND unusually high for this particular asset.
    importances = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS)
    result["top_factors"] = [
        _top_factors(features_df.iloc[i], importances) for i in range(len(features_df))
    ]

    return result.sort_values("composite_risk", ascending=False).reset_index(drop=True)


def _top_factors(feature_row, importances, n=3):
    scored = {col: importances[col] * _normalise(col, feature_row[col]) for col in FEATURE_COLUMNS}
    top = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)[:n]
    labels = {
        "max_wind_experienced_mph": f"high wind exposure ({feature_row['max_wind_experienced_mph']:.0f} mph)",
        "storm_surge_exposure": "storm-surge exposure",
        "age_years": f"asset age ({feature_row['age_years']:.0f} yrs)",
        "years_since_inspection": f"overdue inspection ({feature_row['years_since_inspection']:.0f} yrs since last)",
        "prior_outage_count": f"prior outage history ({feature_row['prior_outage_count']:.0f} events)",
        "vegetation_density": "dense nearby vegetation",
        "flood_zone": "located in a flood zone",
        "distance_to_coast_km": "proximity to coast",
    }
    return [labels[col] for col, _ in top]


def _normalise(col, val):
    # Just for ranking factors against each other in the explainability panel (has no effect on the model's actual predictions).
    scales = {
        "max_wind_experienced_mph": 150,
        "storm_surge_exposure": 1,
        "age_years": 60,
        "years_since_inspection": 10,
        "prior_outage_count": 5,
        "vegetation_density": 1,
        "flood_zone": 1,
        "distance_to_coast_km": -100,  # closer to coast = higher contribution
    }
    scale = scales[col]
    if scale < 0:
        return max(0.0, 1 - val / abs(scale))
    return min(1.0, val / scale)
