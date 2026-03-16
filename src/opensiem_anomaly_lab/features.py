import pandas as pd


TARGET_COLUMNS = [
    "label",
    "attempted_category",
]

IDENTIFIER_COLUMNS = [
    "src_ip_dec",
    "src_port",
    "dst_ip_dec",
    "dst_port",
    "timestamp",
]


def drop_known_non_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols_to_drop = [col for col in TARGET_COLUMNS + IDENTIFIER_COLUMNS if col in df.columns]
    return df.drop(columns=cols_to_drop)


def keep_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=["number"]).copy()


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    return df.fillna(0)


def prepare_feature_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_known_non_feature_columns(df)
    df = keep_numeric_columns(df)
    df = fill_missing_values(df)
    return df