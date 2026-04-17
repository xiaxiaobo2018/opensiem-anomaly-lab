from __future__ import annotations

import numpy as np
import pandas as pd

from opensiem_anomaly_lab.ingestion import normalize_column_name


METADATA_COLUMNS = [
    "scenario_name",
    "fault_label",
    "fault_family",
    "fault_type",
    "is_anomaly",
    "timestamp",
]

AGGREGATION_FUNCTIONS = ["mean", "std", "min", "max"]


def prepare_feature_dataframe(metric_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        metric_df.groupby(METADATA_COLUMNS + ["metric_name"], dropna=False)["value"]
        .agg(AGGREGATION_FUNCTIONS)
        .reset_index()
    )

    feature_df = grouped.pivot_table(
        index=METADATA_COLUMNS,
        columns="metric_name",
        values=AGGREGATION_FUNCTIONS,
        fill_value=0,
    )

    feature_df.columns = [
        f"{stat}__{normalize_column_name(metric_name)}"
        for stat, metric_name in feature_df.columns.to_flat_index()
    ]
    feature_df = feature_df.reset_index()

    numeric_columns = [column for column in feature_df.columns if column not in METADATA_COLUMNS]
    feature_df[numeric_columns] = feature_df[numeric_columns].replace([np.inf, -np.inf], np.nan).fillna(0)

    return feature_df.sort_values(["scenario_name", "timestamp"]).reset_index(drop=True)
