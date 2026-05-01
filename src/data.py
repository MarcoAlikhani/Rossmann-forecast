"""Data loading and preprocessing."""
import pandas as pd
import hashlib
from pathlib import Path


def load_raw_data(train_path: str, store_path: str) -> pd.DataFrame:
    """Load and merge raw Rossmann data."""
    train = pd.read_csv(train_path, low_memory=False)
    store = pd.read_csv(store_path)
    df = train.merge(store, on="Store", how="left")
    return df


def preprocess(
    df: pd.DataFrame,
    drop_columns: list,
    drop_zero_sales: bool = True,
    fill_na_value: float = 0,
) -> pd.DataFrame:
    """Clean and prepare data for modeling."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    if drop_zero_sales:
        df = df[df["Sales"] > 0].copy()

    df = df.fillna(fill_na_value)
    df = df.drop(columns=drop_columns)

    return df


def time_aware_split(df: pd.DataFrame, test_size_fraction: float = 0.2):
    """Split chronologically — no leakage."""
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    split_date = df_sorted["Date"].quantile(1 - test_size_fraction)

    train_df = df_sorted[df_sorted["Date"] < split_date].copy()
    test_df = df_sorted[df_sorted["Date"] >= split_date].copy()

    return train_df, test_df, split_date


def hash_dataframe(df: pd.DataFrame) -> str:
    """Compute a stable hash of a dataframe — for data versioning."""
    return hashlib.sha256(
        pd.util.hash_pandas_object(df, index=True).values.tobytes()
    ).hexdigest()[:12]


def hash_file(path: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]