"""
Trains the risk model on training_data.csv and saves it to risk_model.pkl.
Run from prototype/: python model/train_risk_model.py (needs data/generate_data.py run first)
"""

import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from risk_scoring import FEATURE_COLUMNS, train_model  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main():
    training_path = DATA_DIR / "training_data.csv"
    if not training_path.exists():
        raise SystemExit("training_data.csv not found. Run data/generate_data.py first.")

    df = pd.read_csv(training_path)

    train_df, test_df = train_test_split(df, test_size=0.25, random_state=42, stratify=df["failed"])

    model = train_model(train_df)

    test_probs = model.predict_proba(test_df[FEATURE_COLUMNS])[:, 1]
    auc = roc_auc_score(test_df["failed"], test_probs)

    print(f"Trained on {len(train_df)} examples, validated on {len(test_df)} held-out examples.")
    print(f"Held-out AUC: {auc:.3f}")
    print("Feature importances:")
    for col, imp in sorted(zip(FEATURE_COLUMNS, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {col:<28} {imp:.3f}")


if __name__ == "__main__":
    main()
