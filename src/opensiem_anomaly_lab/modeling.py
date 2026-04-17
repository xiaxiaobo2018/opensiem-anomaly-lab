from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from opensiem_anomaly_lab.features import METADATA_COLUMNS


DEFAULT_RANDOM_STATE = 42


def get_feature_columns(feature_df: pd.DataFrame) -> list[str]:
    return [column for column in feature_df.columns if column not in METADATA_COLUMNS]


def split_feature_dataframe(
    feature_df: pd.DataFrame,
    train_fraction: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    normal_df = (
        feature_df[feature_df["is_anomaly"] == 0]
        .sort_values(["scenario_name", "timestamp"])
        .reset_index(drop=True)
    )
    anomaly_df = (
        feature_df[feature_df["is_anomaly"] == 1]
        .sort_values(["scenario_name", "timestamp"])
        .reset_index(drop=True)
    )

    if normal_df.empty:
        raise ValueError("No normal observations were found. Isolation Forest needs normal training data.")
    if len(normal_df) < 4:
        raise ValueError("Need at least 4 normal observations to split train and evaluation windows.")

    train_size = int(len(normal_df) * train_fraction)
    train_size = max(1, min(train_size, len(normal_df) - 1))

    train_df = normal_df.iloc[:train_size].copy()
    holdout_normal_df = normal_df.iloc[train_size:].copy()
    evaluation_df = pd.concat([holdout_normal_df, anomaly_df], ignore_index=True)

    return train_df, evaluation_df


def train_isolation_forest(
    feature_df: pd.DataFrame,
    train_fraction: float = 0.7,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[IsolationForest, pd.DataFrame, pd.DataFrame, list[str]]:
    train_df, evaluation_df = split_feature_dataframe(feature_df, train_fraction=train_fraction)
    feature_columns = get_feature_columns(feature_df)
    model = IsolationForest(
        contamination="auto",
        n_estimators=300,
        random_state=random_state,
    )
    model.fit(train_df[feature_columns])
    return model, train_df, evaluation_df, feature_columns


def score_feature_dataframe(
    model: IsolationForest,
    feature_df: pd.DataFrame,
    feature_columns: list[str],
) -> pd.DataFrame:
    scored_df = feature_df.copy()
    scored_df["anomaly_score"] = -model.decision_function(scored_df[feature_columns])
    scored_df["predicted_is_anomaly"] = (model.predict(scored_df[feature_columns]) == -1).astype(int)
    return scored_df


def evaluate_predictions(scored_df: pd.DataFrame) -> dict[str, Any]:
    y_true = scored_df["is_anomaly"].astype(int).to_numpy()
    y_pred = scored_df["predicted_is_anomaly"].astype(int).to_numpy()
    anomaly_scores = scored_df["anomaly_score"].astype(float).to_numpy()

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    metrics: dict[str, Any] = {
        "observations": int(len(scored_df)),
        "normal_observations": int((y_true == 0).sum()),
        "anomalous_observations": int((y_true == 1).sum()),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "mean_anomaly_score": float(anomaly_scores.mean()),
    }

    if np.unique(y_true).size > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, anomaly_scores))
        metrics["average_precision"] = float(average_precision_score(y_true, anomaly_scores))

    return metrics


def build_scenario_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    summary_df = (
        scored_df.groupby(
            ["scenario_name", "fault_label", "fault_family", "fault_type", "is_anomaly"],
            as_index=False,
        )
        .agg(
            windows=("timestamp", "size"),
            mean_anomaly_score=("anomaly_score", "mean"),
            max_anomaly_score=("anomaly_score", "max"),
            predicted_anomaly_rate=("predicted_is_anomaly", "mean"),
        )
        .sort_values(["is_anomaly", "mean_anomaly_score"], ascending=[False, False])
        .reset_index(drop=True)
    )
    return summary_df
