"""Model training and evaluation."""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


def train_model(X_train, y_train, params: dict) -> RandomForestRegressor:
    """Train a RandomForestRegressor with given params."""
    model = RandomForestRegressor(**params)
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test) -> dict:
    """Compute MAE and baseline comparisons."""
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)

    # Baseline: predict the mean
    baseline_mean_mae = mean_absolute_error(
        y_test, np.full_like(y_test, y_test.mean(), dtype=float)
    )

    return {
        "mae": float(mae),
        "baseline_mean_mae": float(baseline_mean_mae),
        "lift_over_mean_pct": float((1 - mae / baseline_mean_mae) * 100),
    }