"""Model training and evaluation."""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit


def train_model(X_train, y_train, params: dict) -> RandomForestRegressor:
    """Train a RandomForestRegressor with given params."""
    model = RandomForestRegressor(**params)
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test) -> dict:
    """Compute MAE and baseline comparisons."""
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)

    baseline_mean_mae = mean_absolute_error(
        y_test, np.full_like(y_test, y_test.mean(), dtype=float)
    )

    return {
        "mae": float(mae),
        "baseline_mean_mae": float(baseline_mean_mae),
        "lift_over_mean_pct": float((1 - mae / baseline_mean_mae) * 100),
    }


def time_series_cross_validate(
    df_sorted, feature_cols: list, target_col: str, params: dict, n_splits: int = 5
) -> dict:
    """
    Rolling-origin time-series cross-validation.

    Each fold: train on [start ... t], test on [t ... t+window].
    The training window grows; the test window slides forward in time.
    This mirrors how the model will actually be used in production.
    """
    df_sorted = df_sorted.sort_values("Date").reset_index(drop=True)
    X = df_sorted[feature_cols]
    y = df_sorted[target_col]

    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_maes = []
    fold_lifts = []

    for fold_idx, (train_idx, test_idx) in enumerate(tscv.split(X), start=1):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

        model = RandomForestRegressor(**params)
        model.fit(X_tr, y_tr)
        preds = model.predict(X_te)

        mae = mean_absolute_error(y_te, preds)
        baseline = mean_absolute_error(y_te, np.full_like(y_te, y_te.mean(), dtype=float))
        lift = (1 - mae / baseline) * 100

        fold_maes.append(mae)
        fold_lifts.append(lift)
        print(f"   Fold {fold_idx}: MAE={mae:.2f}, lift over mean={lift:.1f}%")

    return {
        "n_splits": n_splits,
        "fold_maes": [float(m) for m in fold_maes],
        "mae_mean": float(np.mean(fold_maes)),
        "mae_std": float(np.std(fold_maes)),
        "lift_mean_pct": float(np.mean(fold_lifts)),
        "lift_std_pct": float(np.std(fold_lifts)),
    }