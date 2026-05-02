"""Train the forecasting model end-to-end. One command, fully reproducible."""

import json
import random
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import yaml

from src.data import (
    hash_dataframe,
    hash_file,
    load_raw_data,
    preprocess,
    time_aware_split,
)
from src.features import build_features
from src.model import evaluate, time_series_cross_validate, train_model


def set_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)


def main():
    with open("configs/config.yaml") as f:
        config = yaml.safe_load(f)

    set_seeds(config["seed"])

    print("📥 Loading data...")
    df = load_raw_data(config["data"]["raw_train"], config["data"]["raw_store"])
    print(f"   Loaded {len(df):,} rows")

    print("🧹 Preprocessing...")
    df_clean = preprocess(
        df,
        drop_columns=config["preprocessing"]["drop_columns"],
        drop_zero_sales=config["preprocessing"]["drop_zero_sales"],
        fill_na_value=config["preprocessing"]["fill_na_value"],
    )
    data_hash = hash_dataframe(df_clean)
    print(f"   Cleaned data hash: {data_hash}")

    print("✂️  Time-aware split...")
    train_df, test_df, split_date = time_aware_split(
        df_clean, config["split"]["test_size_fraction"]
    )
    print(f"   Split at {split_date.date()} → train: {len(train_df):,}, test: {len(test_df):,}")

    X_train, y_train = build_features(train_df)
    X_test, y_test = build_features(test_df)

    print("🤖 Training final model on full train set...")
    model = train_model(X_train, y_train, config["model_params"])

    print("📊 Evaluating on holdout...")
    metrics = evaluate(model, X_test, y_test)
    print(f"   MAE: {metrics['mae']:.2f}")
    print(f"   Baseline (mean) MAE: {metrics['baseline_mean_mae']:.2f}")
    print(f"   Lift over mean: {metrics['lift_over_mean_pct']:.1f}%")

    print("🔄 Time-series cross-validation (5 folds)...")
    cv_metrics = time_series_cross_validate(
        df_clean,
        feature_cols=X_train.columns.tolist(),
        target_col="Sales",
        params=config["model_params"],
        n_splits=5,
    )
    print(f"   CV MAE: {cv_metrics['mae_mean']:.2f} ± {cv_metrics['mae_std']:.2f}")
    print(f"   CV lift: {cv_metrics['lift_mean_pct']:.1f}% ± {cv_metrics['lift_std_pct']:.1f}%")

    print("💾 Saving model + metadata...")
    Path("models").mkdir(exist_ok=True)
    joblib.dump(model, config["model"]["output_path"])

    metadata = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "data_hash": data_hash,
        "raw_train_hash": hash_file(config["data"]["raw_train"]),
        "raw_store_hash": hash_file(config["data"]["raw_store"]),
        "feature_columns": X_train.columns.tolist(),
        "target": "Sales",
        "split_date": str(split_date),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "model_params": config["model_params"],
        "metrics": metrics,
        "cv_metrics": cv_metrics,
        "seed": config["seed"],
    }
    with open(config["model"]["metadata_path"], "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Done. Model saved to {config['model']['output_path']}")
    print(f"   Metadata saved to {config['model']['metadata_path']}")


if __name__ == "__main__":
    main()
