"""Feature engineering."""
import pandas as pd

TARGET = "Sales"
DROP_FOR_FEATURES = ["Sales", "Date", "Customers"]


def build_features(df: pd.DataFrame):
    """Split a preprocessed dataframe into X and y."""
    y = df[TARGET]
    X = df.drop(columns=DROP_FOR_FEATURES)
    return X, y