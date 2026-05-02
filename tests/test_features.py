"""Tests for src/features.py — X/y construction."""
import pandas as pd

from src.features import build_features, TARGET, DROP_FOR_FEATURES


def test_build_features_returns_x_and_y():
    df = pd.DataFrame({
        "Sales": [100, 200],
        "Date": pd.to_datetime(["2015-01-01", "2015-01-02"]),
        "Customers": [10, 20],
        "Store": [1, 2],
        "Promo": [0, 1],
    })
    X, y = build_features(df)
    assert "Sales" not in X.columns, "Target leaked into features"
    assert "Date" not in X.columns, "Date is not a feature"
    assert "Customers" not in X.columns, "Customers leaks future info"
    assert (y == df["Sales"]).all()


def test_build_features_constants_correct():
    """Sanity check on the module-level constants."""
    assert TARGET == "Sales"
    assert "Sales" in DROP_FOR_FEATURES
    assert "Customers" in DROP_FOR_FEATURES