from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import zipfile

import fsspec
import numpy as np
import pandas as pd


RAW_ANOMOD_ZIP = Path("data/anomod/AnoMod.zip")
RAW_ANOMOD_DIR = Path("data/raw/anomod")
PROCESSED_DIR = Path("data/processed")
METRIC_DATA_ROOT = Path("TT_data/metric_data")
DEFAULT_ANOMOD_GCS_PREFIX = "gs://opensiem-data-xia0b0/raw/anomod"


def normalize_column_name(name: str) -> str:
    name = name.strip().lower()
    name = name.replace("/", "_per_")
    name = name.replace("-", "_")
    name = re.sub(r"[^\w]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    return df


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def strip_run_suffix(scenario_name: str) -> str:
    scenario_name = re.sub(r"_\d{8}T\d{6}Z(?:_em)?$", "", scenario_name)
    scenario_name = re.sub(r"_em$", "", scenario_name)
    return scenario_name


def parse_scenario_metadata(scenario_name: str) -> dict[str, object]:
    base_name = strip_run_suffix(scenario_name)

    if base_name.lower().startswith("normal_case"):
        return {
            "scenario_name": scenario_name,
            "fault_label": "normal_case",
            "fault_family": "normal",
            "fault_type": "normal",
            "is_anomaly": 0,
        }

    match = re.match(r"^Lv_(?P<family>[^_]+)_(?P<fault>.+)$", base_name)
    if not match:
        return {
            "scenario_name": scenario_name,
            "fault_label": normalize_column_name(base_name),
            "fault_family": "unknown",
            "fault_type": "unknown",
            "is_anomaly": 1,
        }

    return {
        "scenario_name": scenario_name,
        "fault_label": normalize_column_name(base_name),
        "fault_family": normalize_column_name(match.group("family")),
        "fault_type": normalize_column_name(match.group("fault")),
        "is_anomaly": 1,
    }


def get_anomod_gcs_prefix() -> str | None:
    prefix = os.getenv("ANOMOD_GCS_PREFIX", DEFAULT_ANOMOD_GCS_PREFIX).strip()
    return prefix.rstrip("/") if prefix else None


def extract_anomod_archive(
    zip_path: Path = RAW_ANOMOD_ZIP,
    extract_to: Path = RAW_ANOMOD_DIR,
) -> bool:
    metric_dir = extract_to / METRIC_DATA_ROOT
    if metric_dir.exists():
        return False

    if not zip_path.exists():
        raise FileNotFoundError(f"Could not find AnoMod archive at {zip_path}")

    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    return True


def list_metric_sources(
    gcs_prefix: str | None = None,
    zip_path: Path = RAW_ANOMOD_ZIP,
    extracted_dir: Path = RAW_ANOMOD_DIR,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metric_dir = extracted_dir / METRIC_DATA_ROOT
    gcs_prefix = get_anomod_gcs_prefix() if gcs_prefix is None else gcs_prefix

    if metric_dir.exists():
        for path in sorted(metric_dir.rglob("*metrics*.csv")):
            scenario_name = path.parent.name
            rows.append(
                {
                    **parse_scenario_metadata(scenario_name),
                    "source_kind": "filesystem",
                    "source_path": str(path),
                }
            )
    elif gcs_prefix:
        fs = fsspec.filesystem("gcs")
        pattern = f"{gcs_prefix}/{METRIC_DATA_ROOT.as_posix()}/*/*metrics*.csv"

        for path in sorted(fs.glob(pattern)):
            gcs_path = path if path.startswith("gs://") else f"gs://{path}"
            scenario_name = PurePosixPath(gcs_path).parent.name
            rows.append(
                {
                    **parse_scenario_metadata(scenario_name),
                    "source_kind": "gcs",
                    "source_path": gcs_path,
                }
            )
    elif zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            for name in sorted(zf.namelist()):
                if not name.startswith(f"{METRIC_DATA_ROOT.as_posix()}/") or not name.endswith(".csv"):
                    continue

                scenario_name = PurePosixPath(name).parent.name
                rows.append(
                    {
                        **parse_scenario_metadata(scenario_name),
                        "source_kind": "zip",
                        "source_path": name,
                    }
                )
    else:
        raise FileNotFoundError(
            "AnoMod metric data not found. Expected either a GCS prefix such as "
            f"{DEFAULT_ANOMOD_GCS_PREFIX}, an extracted archive under {metric_dir}, "
            f"or a zip file at {zip_path}."
        )

    manifest_df = pd.DataFrame(rows).sort_values(["is_anomaly", "scenario_name"]).reset_index(drop=True)
    return manifest_df


def save_metric_manifest(
    gcs_prefix: str | None = None,
    zip_path: Path = RAW_ANOMOD_ZIP,
    extracted_dir: Path = RAW_ANOMOD_DIR,
    output_path: Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    manifest_df = list_metric_sources(
        gcs_prefix=gcs_prefix,
        zip_path=zip_path,
        extracted_dir=extracted_dir,
    )
    output_path = output_path or PROCESSED_DIR / "anomod_metric_manifest.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_df.to_csv(output_path, index=False)
    return manifest_df, output_path


def read_metric_frame(
    source_path: str,
    source_kind: str,
    scenario_name: str,
    zip_path: Path = RAW_ANOMOD_ZIP,
) -> pd.DataFrame:
    usecols = ["metric_name", "timestamp", "value"]

    if source_kind == "filesystem":
        df = pd.read_csv(source_path, usecols=usecols, low_memory=False)
    elif source_kind == "gcs":
        df = pd.read_csv(source_path, usecols=usecols, low_memory=False)
    elif source_kind == "zip":
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(source_path) as fh:
                df = pd.read_csv(fh, usecols=usecols, low_memory=False)
    else:
        raise ValueError(f"Unsupported source kind: {source_kind}")

    df = normalize_columns(df)
    df = basic_clean(df)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["metric_name", "timestamp", "value"]).copy()
    df["timestamp"] = df["timestamp"].astype("int64")

    metadata = parse_scenario_metadata(scenario_name)
    for key, value in metadata.items():
        df[key] = value

    ordered_columns = [
        "scenario_name",
        "fault_label",
        "fault_family",
        "fault_type",
        "is_anomaly",
        "timestamp",
        "metric_name",
        "value",
    ]
    return df[ordered_columns]
