from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from opensiem_anomaly_lab.ingestion import METRIC_DATA_ROOT, RAW_ANOMOD_DIR, get_anomod_gcs_prefix


def main() -> None:
    gcs_prefix = get_anomod_gcs_prefix()
    if not gcs_prefix:
        raise ValueError("ANOMOD_GCS_PREFIX is empty. Set it to a valid gs:// bucket prefix.")

    local_target = RAW_ANOMOD_DIR / METRIC_DATA_ROOT
    local_target.parent.mkdir(parents=True, exist_ok=True)

    gcloud_path = shutil.which("gcloud")
    if gcloud_path is None:
        raise FileNotFoundError(
            "Could not find `gcloud` in PATH. Install the Google Cloud CLI to sync the local AnoMod cache."
        )

    source = f"{gcs_prefix}/{METRIC_DATA_ROOT.as_posix()}"
    command = [
        gcloud_path,
        "storage",
        "rsync",
        "--recursive",
        source,
        str(local_target),
    ]

    print(f"Syncing AnoMod metric cache from: {source}")
    print(f"Local target: {local_target}")
    subprocess.run(command, check=True)
    print("Sync complete.")


if __name__ == "__main__":
    main()
