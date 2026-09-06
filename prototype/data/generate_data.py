"""
Generates the mocked datasets: assets.csv, crews.csv, helene_track.csv, and training_data.csv.
Run from prototype/: python data/generate_data.py 
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from risk_scoring import build_features  # noqa: E402

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).parent

# Landfall (~10 mi WSW of Perry, FL, 03:10 UTC Sept 27 2024, Cat 4, 140 mph) and the general path through Georgia into Asheville, NC are real and well documented.
# Points in between are interpolated rather than pulled from a full HURDAT2 file.
HELENE_TRACK = [
    {"datetime": "2024-09-26 12:00", "lat": 26.50, "lon": -85.00, "max_wind_mph": 100, "category": 2, "label": "Gulf of Mexico"},
    {"datetime": "2024-09-26 18:00", "lat": 28.00, "lon": -84.50, "max_wind_mph": 120, "category": 3, "label": "Approaching Big Bend, FL"},
    {"datetime": "2024-09-27 00:00", "lat": 29.30, "lon": -84.05, "max_wind_mph": 140, "category": 4, "label": "Peak intensity, offshore"},
    {"datetime": "2024-09-27 03:10", "lat": 30.06, "lon": -83.83, "max_wind_mph": 140, "category": 4, "label": "Landfall near Perry, FL"},
    {"datetime": "2024-09-27 05:00", "lat": 30.90, "lon": -83.40, "max_wind_mph": 100, "category": 2, "label": "Crossing into Georgia"},
    {"datetime": "2024-09-27 09:00", "lat": 32.00, "lon": -83.00, "max_wind_mph": 70, "category": 1, "label": "East-central Georgia"},
    {"datetime": "2024-09-27 15:00", "lat": 33.80, "lon": -82.70, "max_wind_mph": 55, "category": 0, "label": "Georgia / South Carolina border"},
    {"datetime": "2024-09-27 21:00", "lat": 35.60, "lon": -82.55, "max_wind_mph": 45, "category": 0, "label": "Asheville, NC area"},
    {"datetime": "2024-09-28 00:00", "lat": 36.30, "lon": -84.00, "max_wind_mph": 40, "category": 0, "label": "Southern Kentucky / East Tennessee"},
    {"datetime": "2024-09-28 18:00", "lat": 36.00, "lon": -86.50, "max_wind_mph": 25, "category": 0, "label": "Dissipated, north-central Tennessee"},
]

# Fictional SGW service hubs, loosely anchored to real places along
# Helene's path so the storm actually crosses SGW's territory.
HUBS = [
    {"name": "Big Bend Coastal", "lat": 30.05, "lon": -83.85, "dist_coast_km": 4, "veg": 0.35, "flood_bias": 0.5},
    {"name": "Valdosta Corridor", "lat": 30.83, "lon": -83.28, "dist_coast_km": 140, "veg": 0.45, "flood_bias": 0.15},
    {"name": "Macon Area", "lat": 32.84, "lon": -83.63, "dist_coast_km": 240, "veg": 0.4, "flood_bias": 0.1},
    {"name": "Augusta Area", "lat": 33.47, "lon": -82.01, "dist_coast_km": 270, "veg": 0.5, "flood_bias": 0.15},
    {"name": "Upstate SC / Western NC", "lat": 34.90, "lon": -82.30, "dist_coast_km": 330, "veg": 0.65, "flood_bias": 0.25},
    {"name": "Asheville Inland", "lat": 35.60, "lon": -82.55, "dist_coast_km": 400, "veg": 0.75, "flood_bias": 0.45},
]

ASSETS_PER_HUB = 5
N_HISTORICAL_STORMS = 40


def generate_assets():
    rows = []
    asset_num = 1
    for hub in HUBS:
        for _ in range(ASSETS_PER_HUB):
            asset_type = RNG.choice(["Substation", "Transmission Line"], p=[0.6, 0.4])
            lat = hub["lat"] + RNG.normal(0, 0.18)
            lon = hub["lon"] + RNG.normal(0, 0.18)
            age = int(RNG.integers(3, 46))
            # Older assets skew slightly toward longer inspection gaps.
            inspection_gap = min(5, int(RNG.poisson(0.6 + age / 40)))
            prior_outages = int(RNG.poisson(0.3 + age / 30))
            veg = float(np.clip(RNG.normal(hub["veg"], 0.15), 0, 1))
            flood_zone = RNG.random() < hub["flood_bias"]
            is_critical = RNG.random() < 0.15
            customers = int(RNG.integers(2000, 15000)) if asset_type == "Substation" else int(RNG.integers(500, 4000))

            rows.append({
                "asset_id": f"SGW-{asset_num:03d}",
                "name": f"{hub['name']} {asset_type} {asset_num}",
                "asset_type": asset_type,
                "service_area": hub["name"],
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "customers_served": customers,
                "criticality_flag": is_critical,
                "criticality_multiplier": 2.5 if is_critical else 1.0,
                "age_years": age,
                "last_inspection_year": 2024 - inspection_gap,
                "prior_outage_count": prior_outages,
                "vegetation_density": round(veg, 2),
                "flood_zone": bool(flood_zone),
                "distance_to_coast_km": hub["dist_coast_km"] + int(RNG.normal(0, 10)),
            })
            asset_num += 1
    return pd.DataFrame(rows)


def generate_crews(assets_df):
    # One crew per hub, plus two already tied up elsewhere
    # Fewer available crews than high-risk assets, so the optimiser actually has to prioritise instead of just covering everyone.
    rows = []
    crew_num = 1
    for hub in HUBS:
        rows.append({
            "crew_id": f"CREW-{crew_num:02d}",
            "base_name": f"{hub['name']} Depot",
            "base_lat": hub["lat"] + RNG.normal(0, 0.05),
            "base_lon": hub["lon"] + RNG.normal(0, 0.05),
            "available": True,
        })
        crew_num += 1
    # Two additional crews, already deployed on unrelated work.
    for hub in HUBS[:2]:
        rows.append({
            "crew_id": f"CREW-{crew_num:02d}",
            "base_name": f"{hub['name']} Depot (mutual aid)",
            "base_lat": hub["lat"] + RNG.normal(0, 0.05),
            "base_lon": hub["lon"] + RNG.normal(0, 0.05),
            "available": False,
        })
        crew_num += 1
    return pd.DataFrame(rows)


def _synthetic_track(peak_category, region_bounds):
    """A short straight-line track crossing the region, for a fictional past storm."""
    lat_lo, lat_hi, lon_lo, lon_hi = region_bounds
    start_lat = RNG.uniform(lat_lo, lat_hi)
    start_lon = lon_lo - 1.0
    end_lat = start_lat + RNG.uniform(-2.5, 2.5)
    end_lon = lon_hi + 1.0
    peak_wind = {1: 80, 2: 100, 3: 120, 4: 140, 5: 160}[peak_category]
    n_points = 5
    track = []
    for i in range(n_points):
        frac = i / (n_points - 1)
        # Wind ramps up then decays across the fictional storm's passage.
        intensity_frac = 1 - abs(frac - 0.4) / 0.6
        track.append({
            "lat": start_lat + (end_lat - start_lat) * frac,
            "lon": start_lon + (end_lon - start_lon) * frac,
            "max_wind_mph": max(30, peak_wind * max(0.3, intensity_frac)),
            "category": peak_category if intensity_frac > 0.7 else max(0, peak_category - 1),
        })
    return track


def generate_training_data(assets_df):
    region_bounds = (29.0, 36.5, -85.0, -81.5)
    category_weights = [0.35, 0.30, 0.20, 0.10, 0.05]
    rows = []
    for storm_i in range(N_HISTORICAL_STORMS):
        peak_category = RNG.choice([1, 2, 3, 4, 5], p=category_weights)
        track = _synthetic_track(peak_category, region_bounds)
        for _, asset in assets_df.iterrows():
            features = build_features(asset, track)
            logit = (
                -6.0
                + 0.045 * features["max_wind_experienced_mph"]
                + 1.5 * features["storm_surge_exposure"]
                + 0.02 * features["age_years"]
                + 0.15 * features["years_since_inspection"]
                + 0.25 * features["prior_outage_count"]
                + 1.2 * features["vegetation_density"]
                + 0.8 * features["flood_zone"]
                - 0.005 * features["distance_to_coast_km"]
                + RNG.normal(0, 0.5)
            )
            prob = 1 / (1 + np.exp(-logit))
            failed = int(RNG.random() < prob)
            row = {"storm_id": f"HIST-{storm_i+1:03d}", "asset_id": asset["asset_id"], "failed": failed}
            row.update(features)
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    assets_df = generate_assets()
    crews_df = generate_crews(assets_df)
    track_df = pd.DataFrame(HELENE_TRACK)
    training_df = generate_training_data(assets_df)

    assets_df.to_csv(DATA_DIR / "assets.csv", index=False)
    crews_df.to_csv(DATA_DIR / "crews.csv", index=False)
    track_df.to_csv(DATA_DIR / "helene_track.csv", index=False)
    training_df.to_csv(DATA_DIR / "training_data.csv", index=False)

    print(f"Generated {len(assets_df)} assets, {len(crews_df)} crews, "
          f"{len(track_df)} track points, {len(training_df)} training examples "
          f"({training_df['failed'].mean():.1%} historical failure rate).")


if __name__ == "__main__":
    main()
