from pathlib import Path

import pandas as pd

from opensiem_anomaly_lab.features import prepare_feature_dataframe


PROCESSED_DIR = Path("data/processed")


def main() -> None:
    input_path = PROCESSED_DIR / "cicids_sample_clean.csv"
    output_path = PROCESSED_DIR / "cicids_sample_features.csv"

    df = pd.read_csv(input_path)
    feature_df = prepare_feature_dataframe(df)

    feature_df.to_csv(output_path, index=False)

    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print(f"Original shape: {df.shape}")
    print(f"Feature-only shape: {feature_df.shape}")
    print("\nFeature columns:")
    print(feature_df.columns.tolist())


if __name__ == "__main__":
    main()