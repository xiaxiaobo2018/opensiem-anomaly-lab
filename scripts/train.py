from __future__ import annotations

import json
from pathlib import Path
import sys

import joblib
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.ingestion import PROCESSED_DIR
from opensiem_anomaly_lab.modeling import (
    DEFAULT_RANDOM_STATE,
    score_feature_dataframe,
    train_isolation_forest,
)


FEATURE_PATH = PROCESSED_DIR / "anomod_metric_features.csv"
MODEL_PATH = PROCESSED_DIR / "anomod_isolation_forest.joblib"
TRAIN_SCORES_PATH = PROCESSED_DIR / "anomod_train_scores.csv"
TRAINING_SUMMARY_PATH = PROCESSED_DIR / "anomod_training_summary.json"


def main() -> None:
    if not FEATURE_PATH.exists():
        raise FileNotFoundError(
            f"Could not find feature table at {FEATURE_PATH}. Run scripts/prepare_features.py first."
        )

    feature_df = pd.read_csv(FEATURE_PATH)
    model, train_df, evaluation_df, feature_columns = train_isolation_forest(feature_df)
    scored_train_df = score_feature_dataframe(model, train_df, feature_columns)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_columns}, MODEL_PATH)
    scored_train_df.to_csv(TRAIN_SCORES_PATH, index=False)

    training_summary = {
        "feature_path": str(FEATURE_PATH),
        "model_path": str(MODEL_PATH),
        "training_rows": int(len(train_df)),
        "evaluation_rows": int(len(evaluation_df)),
        "feature_count": int(len(feature_columns)),
        "train_fraction": 0.7,
        "random_state": DEFAULT_RANDOM_STATE,
        "mean_train_anomaly_score": float(scored_train_df["anomaly_score"].mean()),
        "max_train_anomaly_score": float(scored_train_df["anomaly_score"].max()),
    }

    with TRAINING_SUMMARY_PATH.open("w", encoding="utf-8") as fh:
        json.dump(training_summary, fh, indent=2)

    print(f"Feature table: {FEATURE_PATH}")
    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved scored training windows to: {TRAIN_SCORES_PATH}")
    print(f"Saved training summary to: {TRAINING_SUMMARY_PATH}")
    print(f"Training rows: {len(train_df)}")
    print(f"Evaluation rows reserved: {len(evaluation_df)}")
    print(f"Feature count: {len(feature_columns)}")


if __name__ == "__main__":
    main()
