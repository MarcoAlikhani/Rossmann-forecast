"""Tests for src/data.py — preprocessing logic."""
import pandas as pd
import pytest

from src.data import (
    hash_dataframe,
    preprocess,
    time_aware_split,
)


@pytest.fixture
def raw_df():
    """Small synthetic dataframe mimicking merged Rossmann data."""
    return pd.DataFrame({
        "Store": [1, 1, 2, 2, 3],
        "DayOfWeek": [1, 2, 3, 4, 5],
        "Date": ["2015-01-01", "2015-01-02", "2015-01-03", "2015-01-04", "2015-01-05"],
        "Sales": [100, 0, 200, 150, 300],  # one zero-sales row
        "Customers": [10, 0, 20, 15, 30],
        "Open": [1, 0, 1, 1, 1],
        "Promo": [0, 0, 1, 1, 0],
        "StateHoliday": ["0", "0", "0", "0", "0"],
        "SchoolHoliday": [0, 0, 0, 1, 0],
        "StoreType": ["a", "a", "b", "b", "c"],
        "Assortment": ["a", "a", "b", "b", "c"],
        "PromoInterval": [None, None, "Jan,Apr,Jul,Oct", None, None],
        "CompetitionDistance": [100.0, 100.0, 200.0, 200.0, None],
    })


def test_preprocess_drops_zero_sales(raw_df):
    """Cleanup must drop rows where Sales == 0."""
    out = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    assert (out["Sales"] > 0).all(), "Zero-sales rows should be dropped"
    assert len(out) == 4, "One row dropped from 5"


def test_preprocess_parses_dates(raw_df):
    """Cleanup must convert Date to datetime."""
    out = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    assert pd.api.types.is_datetime64_any_dtype(out["Date"])


def test_preprocess_drops_specified_columns(raw_df):
    """Cleanup must remove the listed columns."""
    out = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    for col in ["StateHoliday", "StoreType", "Assortment", "PromoInterval"]:
        assert col not in out.columns


def test_preprocess_fills_nans(raw_df):
    """Cleanup must leave no NaN values."""
    out = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    assert not out.isnull().any().any()


def test_time_aware_split_no_overlap(raw_df):
    """Train and test sets must not share any dates."""
    cleaned = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    train, test, split_date = time_aware_split(cleaned, test_size_fraction=0.4)
    assert train["Date"].max() < test["Date"].min(), "Train must end before test begins"


def test_time_aware_split_preserves_all_rows(raw_df):
    """Split must lose no data."""
    cleaned = preprocess(
        raw_df,
        drop_columns=["StateHoliday", "StoreType", "Assortment", "PromoInterval"],
    )
    train, test, _ = time_aware_split(cleaned, test_size_fraction=0.4)
    assert len(train) + len(test) == len(cleaned)


def test_hash_dataframe_is_deterministic(raw_df):
    """Same dataframe must produce same hash."""
    h1 = hash_dataframe(raw_df)
    h2 = hash_dataframe(raw_df.copy())
    assert h1 == h2


def test_hash_dataframe_changes_with_data(raw_df):
    """Different dataframes must produce different hashes."""
    h1 = hash_dataframe(raw_df)
    modified = raw_df.copy()
    modified.loc[0, "Sales"] = 999
    h2 = hash_dataframe(modified)
    assert h1 != h2