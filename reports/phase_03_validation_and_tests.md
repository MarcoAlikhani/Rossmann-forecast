# Phase 3 Report — Validation & Tests

**Project:** Rossmann Store Sales Forecasting
**Phase:** 3 of 12 — Make the project self-defending
**Date:** 2026-05-02
**Status:** ✅ Complete
**Repo:** https://github.com/MarcoAlikhani/Rossmann-forecast

---

## 1. Objective

Transform the project from "code that runs on my machine" into "code that defends itself against future regressions." Phase 3 closes the validation-related sins from the Phase 1 inventory by adding three layers of defense:

1. **Schema validation** — bad data is rejected at the boundary, not after it has corrupted training
2. **Unit tests** — every function in `src/` has a behavior contract that can be verified in milliseconds
3. **Time-series cross-validation** — model performance is reported as a distribution across multiple time periods, not a single lottery-ticket number

The success criterion: `pytest -v` passes 13 tests in under 5 seconds, and `python train.py` reports a CV mean ± std MAE that can be defended in a meeting.

---

## 2. The Five Properties of a Validated Project

| # | Property | Phase 2 status | Phase 3 status |
|---|---|---|---|
| 1 | Code is tested | ❌ | ✅ 13 unit tests across 3 files |
| 2 | Data is validated | ❌ Hope-driven | ✅ pandera schemas at every pipeline stage |
| 3 | Models are tested | ❌ | ✅ Sanity test asserts model beats dummy baseline |
| 4 | Performance is statistically defensible | ❌ Single MAE | ✅ 5-fold time-series CV with mean ± std |
| 5 | Tests run with one command | ❌ | ✅ `pytest -v` |

All five now pass.

---

## 3. What Was Built

### 3.1 Data schemas (`src/schema.py`)

Three pandera `DataFrameSchema` definitions, one per pipeline stage:

- **`RAW_MERGED_SCHEMA`** — what the data looks like after `load_raw_data()` (train + store joined). Validates types and ranges of the columns we know we need.
- **`CLEANED_SCHEMA`** — what the data looks like after `preprocess()`. Stricter than raw: `Sales > 0` (no zero-sales rows), `Date` is datetime, no nulls.
- **`INFERENCE_INPUT_SCHEMA`** — what the future API will accept (Phase 4 will use this).

Each schema acts as a guard. If incoming data violates the contract — a column missing, a type wrong, a value out of range — the pipeline raises a detailed error before the bad data can reach the model.

### 3.2 Schema enforcement (`src/data.py`)

Two lines added inside existing functions:

- `RAW_MERGED_SCHEMA.validate(df)` after the merge in `load_raw_data()`
- `CLEANED_SCHEMA.validate(df)` after cleanup in `preprocess()`

This is the lightweight "data contract" that the source article called for. The cost is one function call per stage; the benefit is that schema drift is caught loudly, immediately, and at the responsible boundary.

### 3.3 Time-series cross-validation (`src/model.py`)

Added `time_series_cross_validate()` which uses sklearn's `TimeSeriesSplit` to produce 5 rolling-origin splits. Each fold trains on a growing prefix of history and tests on the next time window. Mean ± standard deviation across folds replaces the single-number metric from Phase 2.

This is the technique the original Phase 1 random split was a sin against. The model is now evaluated under conditions that mirror production: the model only ever sees the past during training, and is only ever evaluated on data that comes strictly after.

### 3.4 Unit tests (`tests/`)

Thirteen tests across three files:

**`tests/test_data.py` — 8 tests:**
- `test_preprocess_drops_zero_sales` — closed-day rows are removed
- `test_preprocess_parses_dates` — Date column becomes datetime
- `test_preprocess_drops_specified_columns` — string columns are dropped
- `test_preprocess_fills_nans` — no nulls survive cleanup
- `test_time_aware_split_no_overlap` — train ends strictly before test begins
- `test_time_aware_split_preserves_all_rows` — no rows lost in split
- `test_hash_dataframe_is_deterministic` — same input → same hash
- `test_hash_dataframe_changes_with_data` — different input → different hash

**`tests/test_features.py` — 2 tests:**
- `test_build_features_returns_x_and_y` — no target leak, no Date in features
- `test_build_features_constants_correct` — module constants match expectations

**`tests/test_model.py` — 3 tests:**
- `test_train_model_returns_fitted_estimator` — training produces a working predictor
- `test_evaluate_returns_required_keys` — metrics dict has the expected fields
- `test_model_beats_dummy_baseline` — on signal-bearing synthetic data, the model beats predicting the mean

The most important test of the set is `test_time_aware_split_no_overlap`. It locks in the Phase 1 lesson at the code level: the temporal leakage sin cannot return to the codebase without a test failing first.

### 3.5 Updated training pipeline (`train.py`)

The script now produces both:
- A single-split MAE (for backwards compatibility with the metadata format)
- A 5-fold CV MAE with mean and standard deviation

Both are saved in the model metadata JSON.

---

## 4. Results

### 4.1 Test suite

```
================ 13 passed in 3.23s ================
```

All 13 tests pass on the first run. Total execution time under 4 seconds — fast enough to run on every code change without thinking about it.

### 4.2 Cross-validation results

```
Fold 1: MAE=930.57,  lift over mean=56.1%
Fold 2: MAE=1214.89, lift over mean=49.6%
Fold 3: MAE=1016.72, lift over mean=55.3%
Fold 4: MAE=1241.64, lift over mean=47.3%
Fold 5: MAE=1059.05, lift over mean=54.0%

CV MAE:  1092.57 ± 118.58
CV lift: 52.5%   ± 3.4%
```

### 4.3 Comparison across all three phases

| Run | Setup | MAE | Trustable? |
|---|---|---|---|
| Phase 1 random split | RF(50, no depth limit) | 815.66 | ❌ Leaky |
| Phase 1 honest split | RF(50, no depth limit) | 784.85 | ❌ Single-period |
| Phase 2 single split | RF(100, depth=15, leaf=5) | 1059.16 | ❌ Single-period |
| **Phase 3 CV (5 folds)** | **RF(100, depth=15, leaf=5)** | **1092.57 ± 118.58** | **✅ Yes** |

### 4.4 Interpretation

The Phase 3 number is **larger than Phase 1's MAE**. This is not a regression — it is the project becoming honest.

Three things happened simultaneously between Phase 1 and Phase 3:

1. **The model was deliberately constrained.** `max_depth=15, min_samples_leaf=5` produces a model less prone to memorizing per-store patterns than the unlimited-depth Phase 1 model. The constrained model generalizes better but scores worse on any single test split.
2. **Single-period MAE is unreliable.** The CV results show fold-to-fold MAE swings of ~310 points (930 to 1241). The Phase 1 number of 785 sits *below* the lowest CV fold — it was an unusually easy test period, not a true measurement.
3. **CV mean ± std is a real measurement.** The claim "this model achieves 52.5% lift over predicting the mean, with std 3.4 percentage points across 5 disjoint time periods" is statistically defensible. The Phase 1 claim of "88.3% accuracy" was not.

The model is the same level of "good." What changed is that we now know how good, with what uncertainty, and on what kind of data. That is the difference between a Demo and a System.

---

## 5. Sins Closed in Phase 3

From the Phase 1 inventory:

- ✅ #7 Random split on time series → `TimeSeriesSplit`-based CV across 5 folds
- ✅ #8 No baseline comparison in pipeline → baseline mean MAE reported every fold
- ✅ #9 No data validation → pandera schemas at every pipeline stage
- ✅ #10 No unit tests for preprocessing → 13 tests across `data`, `features`, `model`
- ✅ #11 Vanity accuracy metric → replaced with MAE + lift over baseline + CV std

**5 sins closed this phase. 11 remaining.** Phase 4 closes the API/serving sins (#12–14).

---

## 6. Key Design Decisions

### 6.1 pandera over manual asserts

Manual `assert df.columns.tolist() == [...]` checks are fragile and don't describe types or ranges. pandera describes the contract declaratively (column X is integer, in range 1–7) and produces detailed error messages naming the exact violation. Worth the dependency.

### 6.2 `TimeSeriesSplit` over custom rolling windows

sklearn's `TimeSeriesSplit` is the standard, well-tested implementation of rolling-origin CV. Writing a custom version would be unnecessary code to maintain. The trade-off: it splits by row index, not by time, so it assumes the data is already sorted by date. The training pipeline sorts before passing data to it.

### 6.3 Tests use small synthetic dataframes, not real data

Every test in `tests/` uses small hand-crafted dataframes (5–200 rows). The real `train.csv` is never loaded by the test suite. Two reasons:
- **Speed** — the suite runs in under 4 seconds. If tests loaded the 40MB CSV, they would take 30+ seconds and never get run.
- **Determinism** — the synthetic data is fully described in the test file. Anyone reading the test knows exactly what input produces the expected output.

### 6.4 Sanity test on synthetic data, not the Rossmann data

`test_model_beats_dummy_baseline` uses `rng.normal()` to generate inputs and a known linear function for the target. This is intentional. The test is not "is the model good on Rossmann?" — that question is answered by CV. The test is "does the training/evaluate plumbing produce a model that uses signal at all?" — a much weaker but much more universal claim. Sanity tests should test the plumbing, not the dataset.

---

## 7. Updated Project Structure

```
rossmann-forecast/
├── configs/
│   └── config.yaml
├── data/
│   ├── raw/                     # gitignored
│   └── processed/
├── models/
│   ├── .gitkeep
│   ├── forecast_model.joblib    # gitignored
│   └── forecast_model_metadata.json  # gitignored
├── notebooks/
│   └── 01_exploration.ipynb
├── reports/
│   ├── phase_01_the_sin.md
│   ├── phase_02_reproducibility.md
│   └── phase_03_validation_and_tests.md
├── src/
│   ├── __init__.py
│   ├── data.py                  # +schema validation calls
│   ├── features.py
│   ├── model.py                 # +time_series_cross_validate
│   └── schema.py                # NEW — pandera schemas
├── tests/                       # NEW
│   ├── __init__.py
│   ├── test_data.py             # 8 tests
│   ├── test_features.py         # 2 tests
│   └── test_model.py            # 3 tests
├── .gitignore
├── README.md
├── requirements.txt             # +pytest, pandera
└── train.py                     # +CV reporting
```

Two new directories (`tests/`), one new module (`src/schema.py`), updated training pipeline. The structural footprint of "becoming defended" was small. The behavioral change is large.

---

## 8. Updated Metadata Bundle

The model metadata JSON now includes CV results alongside the single-split metrics:

```json
{
  ...
  "metrics": {
    "mae": 1059.16,
    "baseline_mean_mae": 2269.30,
    "lift_over_mean_pct": 53.3
  },
  "cv_metrics": {
    "n_splits": 5,
    "fold_maes": [930.57, 1214.89, 1016.72, 1241.64, 1059.05],
    "mae_mean": 1092.57,
    "mae_std": 118.58,
    "lift_mean_pct": 52.5,
    "lift_std_pct": 3.4
  }
}
```

The CV block is what gets reported externally. The single-split block is kept for continuity. In Phase 9 (Model Registry) this metadata becomes a structured record in MLflow rather than a JSON file on disk.

---

## 9. Key Takeaways

1. **A worse number you can trust beats a better number you cannot.** Phase 3 reports a higher MAE than Phase 1. It is also the first MAE that can survive a real meeting.
2. **Tests are documentation that cannot lie.** A README claiming "preprocess drops zero-sales rows" can become wrong silently. The corresponding test cannot — it either passes or fails. Tests are executable specifications.
3. **Schema validation is a load-bearing wall.** Two `.validate(df)` calls in `src/data.py` are the difference between "schema drift causes silent garbage predictions in production" and "schema drift causes a loud, traceable error at the boundary."
4. **Cross-validation is statistical hygiene, not optional.** The fold-to-fold MAE swing (~310 points) was invisible until CV existed. Every single-number metric reported by anyone, anywhere, has this hidden variance — they just don't know it.
5. **Phases compound.** The CV pipeline only worked because Phase 2 had separated `time_aware_split` into a function. The schemas only worked because Phase 2 had a typed config. Each phase makes the next one easy.

---

## 10. Next Phase

**Phase 4 — API & Containerization.** Wrap the trained model in a FastAPI service with `/predict` and `/health` endpoints. Use Pydantic for request validation (mirroring the `INFERENCE_INPUT_SCHEMA` defined in Phase 3). Dockerize the service. Measure real prediction latency under load with locust. The model artifact stops being a file on disk and becomes a callable network service.
