# Phase 1 Report — "The Sin"

**Project:** Rossmann Store Sales Forecasting
**Phase:** 1 of 12 — Build the deliberately bad notebook
**Date:** 2026-05-01
**Status:** ✅ Complete

---

## 1. Objective

Build an end-to-end ML notebook the *wrong* way on purpose. The goal is not a good model — it is to experience every "notebook sin" first-hand so that subsequent phases (reproducibility, validation, deployment, monitoring) feel motivated instead of bureaucratic.

This phase establishes the **starting point** that the rest of the roadmap will systematically dismantle.

---

## 2. Setup

| Item | Value |
|---|---|
| Dataset | Rossmann Store Sales (Kaggle) |
| Files used | `train.csv` (1.017M rows), `store.csv` (1115 rows) |
| Environment | Python 3.11, virtualenv, Windows |
| Libraries | pandas, numpy, scikit-learn, matplotlib |
| Notebook | `forecast.ipynb` (root folder — itself a sin) |
| Model | RandomForestRegressor, 50 trees, default hyperparameters |
| Training time | ~50 seconds |

---

## 3. Pipeline (as built)

1. Load `train.csv` and `store.csv` with hardcoded relative paths
2. Merge on `Store`
3. Cleanup: parse `Date`, drop `Sales == 0` rows, fill NaN with 0, drop string columns (`StateHoliday`, `StoreType`, `Assortment`, `PromoInterval`)
4. Build `X` by dropping `Sales`, `Date`, `Customers`
5. **Random** train/test split (80/20, `random_state=42`)
6. Train RandomForest
7. Evaluate with MAE and a "vanity accuracy" formula
8. Save model with `pickle.dump(model, open('model.pkl', 'wb'))`

---

## 4. Results

### 4.1 Initial (misleading) result

| Metric | Value |
|---|---|
| MAE (random split) | **815.66** |
| "Accuracy" (1 − MAE/mean) | **88.3%** |

This was the number that "felt good." It is also the number that would have been put on a slide deck and presented to stakeholders in a real-world equivalent of this project.

### 4.2 Baseline comparisons (added after initial result)

| Strategy | MAE | Notes |
|---|---|---|
| Predict the mean of `y_test` | 2,292.66 | Floor for any non-trivial model |
| Predict yesterday's sales (per store) | 1,389.11 | Strong naive time-series baseline |
| RandomForest (random split) | 815.66 | The original "result" |
| RandomForest (time-aware split) | 784.85 | The honest result |

### 4.3 Interpretation

- **vs. mean baseline:** 815 MAE is ~64% better than predicting the mean. Sounds great.
- **vs. yesterday baseline:** 815 MAE is ~41% better than predicting yesterday's sales. This is the more meaningful comparison and is the *actual* business lift the model provides.
- **vs. honest split:** Surprisingly, the time-aware split scored slightly *better* (784 vs 815). This does not mean leakage helped — it means both numbers are unreliable single-point estimates, likely driven by the specific test period chosen and Random Forest's tendency to memorize per-store patterns. Phase 3 will address this with proper time-series cross-validation across multiple folds.

---

## 5. The Three Lies Identified

### Lie #1 — The "accuracy" metric is meaningless

The formula `1 − (MAE / mean(y))` was invented to make a regression result look like a classification accuracy. It has no statistical interpretation, no comparison to a baseline, and no business meaning. A model is only good or bad **relative to a baseline**, never in isolation.

**Lesson:** Every model metric must be reported alongside at least one baseline. Without that, the number is decoration.

### Lie #2 — Temporal leakage from random splitting

`train_test_split` with `random_state=42` interleaves dates from the same store between train and test. The model effectively "peeks at the future" during training because it has seen days that come *after* test days for the same store. In production, this is impossible — the model only ever sees the past.

In this specific run, the leakage did not inflate the score (the honest score was actually slightly better), but this is luck of the draw on this dataset. On a different dataset or different period, the inflation can be 2–3x. The point is: **a number you cannot trust is worse than no number at all.**

**Lesson:** Time series data must be split chronologically, and ideally evaluated with rolling-origin cross-validation across multiple time windows.

### Lie #3 — `model.pkl` is a time bomb

The saved model artifact contains:
- ✅ The fitted estimator
- ❌ No record of which columns it expects
- ❌ No record of column order
- ❌ No sklearn version (pickle breaks across versions)
- ❌ No training data hash or date range
- ❌ No hyperparameter record
- ❌ No reference to the preprocessing code that produced its inputs

If the production API receives a request with the dropped string columns intact, the preprocessing pipeline silently produces a different feature matrix than the model was trained on. The model does not error — it silently returns garbage predictions.

**Lesson:** A model artifact is not a `.pkl` file. It is a `.pkl` file *plus* a schema, *plus* a preprocessing pipeline, *plus* metadata, *plus* a version, all bundled together. Phase 2 begins addressing this; Phase 9 (Model Registry) finishes the job.

---

## 6. Notebook Sins Inventory

A complete catalog of what is wrong with the current `forecast.ipynb`, mapped to the phase that will fix each:

| # | Sin | Will be fixed in |
|---|---|---|
| 1 | Hardcoded file paths | Phase 2 (Reproducibility) |
| 2 | No project structure (everything in root) | Phase 2 |
| 3 | Cells run out of order, hidden state | Phase 2 |
| 4 | Dependencies not pinned | Phase 2 |
| 5 | No `.gitignore`, no git history | Phase 2 |
| 6 | No data versioning | Phase 2 |
| 7 | Random split on time series | Phase 3 (Validation) |
| 8 | No baseline comparison in pipeline | Phase 3 |
| 9 | No data validation (schema, ranges, nulls) | Phase 3 |
| 10 | No unit tests for preprocessing | Phase 3 |
| 11 | Vanity accuracy metric | Phase 3 |
| 12 | No API, no service interface | Phase 4 (Servable) |
| 13 | No input validation at inference | Phase 4 |
| 14 | No containerization | Phase 4 |
| 15 | No latency measurement | Phase 5 (Local Deploy) |
| 16 | No CI/CD | Phase 6 |
| 17 | Not deployed anywhere | Phase 7 |
| 18 | No structured logging or metrics | Phase 8 |
| 19 | Model artifact has no metadata or version | Phase 9 (Model Registry) |
| 20 | No prediction monitoring | Phase 10 |
| 21 | No drift detection | Phase 11 |
| 22 | No retraining pipeline | Phase 12 |

---

## 7. Artifacts Produced

| File | Purpose | Production-ready? |
|---|---|---|
| `forecast.ipynb` | Exploration + training notebook | ❌ No |
| `model.pkl` | Pickled RandomForest | ❌ No |
| `train.csv`, `store.csv` | Raw data, untracked | ❌ No |

None of these will survive Phase 2 in their current form. The notebook will be archived under `notebooks/`, the model will be discarded and rebuilt by a proper training script, and the data will be moved under a versioned `data/` directory.

---

## 8. Key Takeaways

1. **A model number without a baseline is not a result.** The single most important addition to Phase 1 was computing the two baselines. The 815 MAE only acquired meaning once it could be compared to 1,389 (yesterday) and 2,293 (mean).
2. **Random splits on time series cannot be trusted**, even when they happen to give a lower number. The methodology is wrong regardless of the result.
3. **A pickled model is a liability without surrounding context** — schema, preprocessing code, version, training metadata. Production systems treat the model artifact as one component of a larger, versioned bundle.
4. **The gap between "notebook works" and "production works" is not technical sophistication — it is engineering discipline.** Every sin in section 6 is fixed by a habit, not by a clever algorithm.

---

## 9. Next Phase

**Phase 2 — Reproducibility.** Convert the notebook into a proper Python project with `src/` layout, pinned dependencies, YAML configs, deterministic seeds, git initialization, and data versioning. Goal: anyone can clone the repo and reproduce the exact same model with one command.
