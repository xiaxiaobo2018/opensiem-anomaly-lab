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
    build_scenario_summary,
    evaluate_predictions,
    score_feature_dataframe,
    split_feature_dataframe,
)


FEATURE_PATH = PROCESSED_DIR / "anomod_metric_features.csv"
MODEL_PATH = PROCESSED_DIR / "anomod_isolation_forest.joblib"
EVALUATION_SCORES_PATH = PROCESSED_DIR / "anomod_evaluation_scores.csv"
SCENARIO_SUMMARY_PATH = PROCESSED_DIR / "anomod_scenario_summary.csv"
METRICS_PATH = PROCESSED_DIR / "anomod_evaluation_metrics.json"


def main() -> None:
    if not FEATURE_PATH.exists():
        raise FileNotFoundError(
            f"Could not find feature table at {FEATURE_PATH}. Run scripts/prepare_features.py first."
        )
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Could not find trained model at {MODEL_PATH}. Run scripts/train.py first."
        )

    feature_df = pd.read_csv(FEATURE_PATH)
    _, evaluation_df = split_feature_dataframe(feature_df)
    model_bundle = joblib.load(MODEL_PATH)
    scored_df = score_feature_dataframe(
        model_bundle["model"],
        evaluation_df,
        model_bundle["feature_columns"],
    )

    metrics = evaluate_predictions(scored_df)
    scenario_summary_df = build_scenario_summary(scored_df)

    EVALUATION_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    scored_df.to_csv(EVALUATION_SCORES_PATH, index=False)
    scenario_summary_df.to_csv(SCENARIO_SUMMARY_PATH, index=False)
    with METRICS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    print(f"Evaluation scores: {EVALUATION_SCORES_PATH}")
    print(f"Scenario summary: {SCENARIO_SUMMARY_PATH}")
    print(f"Metrics JSON: {METRICS_PATH}")
    print("\nMetrics:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
