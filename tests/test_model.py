"""Tests for src/model.py — training and evaluation."""
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from src.model import evaluate, train_model


def test_train_model_returns_fitted_estimator():
    X = pd.DataFrame(np.random.rand(50, 3), columns=["a", "b", "c"])
    y = pd.Series(np.random.rand(50) * 100)
    params = {"n_estimators": 5, "random_state": 42, "n_jobs": 1}
    model = train_model(X, y, params)
    preds = model.predict(X)
    assert len(preds) == len(y)


def test_evaluate_returns_required_keys():
    X = pd.DataFrame(np.random.rand(50, 3), columns=["a", "b", "c"])
    y = pd.Series(np.random.rand(50) * 100)
    params = {"n_estimators": 5, "random_state": 42, "n_jobs": 1}
    model = train_model(X, y, params)
    metrics = evaluate(model, X, y)
    for key in ["mae", "baseline_mean_mae", "lift_over_mean_pct"]:
        assert key in metrics


def test_model_beats_dummy_baseline():
    """A real model on signal-bearing data must beat predicting the mean."""
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(200, 3)), columns=["a", "b", "c"])
    # Create signal: y is a real function of X plus noise
    y = pd.Series(2 * X["a"] - 3 * X["b"] + rng.normal(scale=0.1, size=200))

    params = {"n_estimators": 30, "random_state": 42, "n_jobs": 1}
    model = train_model(X, y, params)
    metrics = evaluate(model, X, y)

    dummy = DummyRegressor(strategy="mean").fit(X, y)
    dummy_preds = dummy.predict(X)
    dummy_mae = np.mean(np.abs(y - dummy_preds))

    assert metrics["mae"] < dummy_mae, "Model must beat the dummy baseline"