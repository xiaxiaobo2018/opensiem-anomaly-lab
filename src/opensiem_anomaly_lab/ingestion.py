from pathlib import Path
import re

import numpy as np
import pandas as pd
from datasets import load_dataset


PROCESSED_DIR = Path("data/processed")


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


def ingest_cicids() -> tuple[Path, Path]:
    ds = load_dataset("bvk/CICIDS-2017")
    df = ds["train"].to_pandas()

    df = normalize_columns(df)
    df = basic_clean(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    sample_path = PROCESSED_DIR / "cicids_sample_clean.csv"
    full_path = PROCESSED_DIR / "cicids_full_clean.parquet"

    sample_df = df.sample(n=5000, random_state=42)

    sample_df.to_csv(sample_path, index=False)
    df.to_parquet(full_path, index=False)

    print(f"Saved sample CSV to: {sample_path}")
    print(f"Saved full Parquet to: {full_path}")
    print(f"Full dataset shape: {df.shape}")
    print(f"Sample dataset shape: {sample_df.shape}")
    print("\nFirst 15 normalized columns:")
    print(df.columns.tolist()[:15])

    if "label" in df.columns:
        print("\nTop label counts:")
        print(df["label"].value_counts(dropna=False).head(10))

    return sample_path, full_path