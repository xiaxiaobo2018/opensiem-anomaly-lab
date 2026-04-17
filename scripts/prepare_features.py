from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.features import prepare_feature_dataframe
from opensiem_anomaly_lab.ingestion import (
    METRIC_DATA_ROOT,
    PROCESSED_DIR,
    RAW_ANOMOD_DIR,
    get_anomod_gcs_prefix,
    save_metric_manifest,
    read_metric_frame,
)


FEATURE_OUTPUT_PATH = PROCESSED_DIR / "anomod_metric_features.csv"


def main() -> None:
    gcs_prefix = get_anomod_gcs_prefix()
    manifest_df, manifest_path = save_metric_manifest(gcs_prefix=gcs_prefix)
    local_metric_dir = RAW_ANOMOD_DIR / METRIC_DATA_ROOT

    scenario_feature_frames: list[pd.DataFrame] = []
    for row in manifest_df.itertuples(index=False):
        metric_df = read_metric_frame(
            source_path=row.source_path,
            source_kind=row.source_kind,
            scenario_name=row.scenario_name,
        )
        scenario_features = prepare_feature_dataframe(metric_df)
        scenario_feature_frames.append(scenario_features)
        print(
            f"{row.scenario_name}: {len(metric_df):,} metric rows -> "
            f"{len(scenario_features):,} timestamp windows"
        )

    feature_df = pd.concat(scenario_feature_frames, ignore_index=True)
    feature_df = feature_df.sort_values(["scenario_name", "timestamp"]).reset_index(drop=True)

    FEATURE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(FEATURE_OUTPUT_PATH, index=False)

    feature_columns = [
        column
        for column in feature_df.columns
        if column not in {"scenario_name", "fault_label", "fault_family", "fault_type", "is_anomaly", "timestamp"}
    ]

    print(f"\nMetric manifest saved to: {manifest_path}")
    print(f"Local metric cache: {local_metric_dir}")
    print(f"GCS fallback source: {gcs_prefix}")
    print(
        "Raw metric source used this run: "
        f"{'local cache' if local_metric_dir.exists() else 'gcs fallback'}"
    )
    print(f"Feature table saved to: {FEATURE_OUTPUT_PATH}")
    print(f"Feature table shape: {feature_df.shape}")
    print(f"Feature columns: {len(feature_columns)}")
    print("\nObservation counts by label:")
    print(feature_df["is_anomaly"].value_counts(dropna=False).rename(index={0: "normal", 1: "anomaly"}))


if __name__ == "__main__":
    main()
