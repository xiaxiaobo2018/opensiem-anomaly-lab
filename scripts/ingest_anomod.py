from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.ingestion import (
    DEFAULT_ANOMOD_GCS_PREFIX,
    RAW_ANOMOD_DIR,
    METRIC_DATA_ROOT,
    get_anomod_gcs_prefix,
    save_metric_manifest,
)


def main() -> None:
    gcs_prefix = get_anomod_gcs_prefix()
    manifest_df, manifest_path = save_metric_manifest(gcs_prefix=gcs_prefix)
    local_metric_dir = RAW_ANOMOD_DIR / METRIC_DATA_ROOT
    preferred_source = "local cache" if local_metric_dir.exists() else "gcs"

    print(f"GCS raw-data prefix: {gcs_prefix or DEFAULT_ANOMOD_GCS_PREFIX}")
    print(f"Local metric cache: {local_metric_dir}")
    print(f"Preferred source for this run: {preferred_source}")
    print(f"Metric manifest: {manifest_path}")
    print(f"Discovered metric scenarios: {len(manifest_df)}")
    print(f"Normal scenarios: {(manifest_df['is_anomaly'] == 0).sum()}")
    print(f"Anomalous scenarios: {(manifest_df['is_anomaly'] == 1).sum()}")
    print("\nScenario manifest:")
    print(
        manifest_df[
            ["scenario_name", "fault_family", "fault_type", "is_anomaly", "source_kind"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
