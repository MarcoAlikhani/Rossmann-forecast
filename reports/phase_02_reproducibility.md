# Phase 2 Report — Reproducibility

**Project:** Rossmann Store Sales Forecasting
**Phase:** 2 of 12 — From notebook to reproducible Python project
**Date:** 2026-05-01
**Status:** ✅ Complete
**Repo:** https://github.com/MarcoAlikhani/Rossmann-forecast

---

## 1. Objective

Convert the Phase 1 notebook into a proper Python project where **anyone** can clone the repo, run a single command, and reproduce the exact same model. This phase fixes the foundational engineering sins (sins #1–6 from the Phase 1 inventory) without yet touching validation, deployment, or monitoring.

The success criterion: `git clone` → `pip install -r requirements.txt` → `python train.py` produces a deterministic, fully-described model artifact.

---

## 2. The Six Properties of a Reproducible Project

Phase 2 measured itself against six concrete reproducibility properties:

| # | Property | Phase 1 status | Phase 2 status |
|---|---|---|---|
| 1 | Anyone can run it | ❌ Hardcoded local paths | ✅ Config-driven, relative paths |
| 2 | Same input → same output | ❌ No seeds | ✅ `random.seed`, `np.random.seed`, model `random_state` |
| 3 | Dependencies pinned | ❌ Loose `pip install` | ✅ `requirements.txt` with exact versions |
| 4 | Configuration separate from code | ❌ Hyperparameters inline | ✅ `configs/config.yaml` |
| 5 | Data version tracked | ❌ "the CSV in my downloads" | ✅ SHA256 hashes of raw + cleaned data in metadata |
| 6 | One command runs everything | ❌ Run cells in order, don't forget cell 7 | ✅ `python train.py` |

All six now pass.

---

## 3. Project Structure

```
rossmann-forecast/
├── configs/
│   └── config.yaml              # all paths, hyperparameters, seed
├── data/
│   ├── raw/                     # gitignored — raw CSVs
│   └── processed/               # gitignored — derived data
├── models/
│   ├── .gitkeep                 # placeholder so folder exists in git
│   ├── forecast_model.joblib    # gitignored — trained model
│   └── forecast_model_metadata.json  # gitignored — schema + metrics + hashes
├── notebooks/
│   └── 01_exploration.ipynb     # Phase 1 sin, archived
├── reports/
│   ├── phase_01_the_sin.md
│   └── phase_02_reproducibility.md
├── src/
│   ├── __init__.py
│   ├── data.py                  # load, preprocess, split, hash
│   ├── features.py              # X/y construction
│   └── model.py                 # train + evaluate
├── tests/                       # empty — Phase 3
├── .gitignore
├── README.md
├── requirements.txt
└── train.py                     # one-command pipeline
```

### Why this layout matters

- **`src/` package**: every helper has a single responsibility and an import path. `data.py` knows nothing about models. `model.py` knows nothing about file paths. This is what makes future testing (Phase 3) and API serving (Phase 4) straightforward.
- **`configs/` separate from code**: hyperparameters can change per environment (local/staging/prod) without modifying source.
- **`notebooks/` for exploration only**: notebooks are fine for EDA and prototyping; they are not suitable for production logic. The Phase 1 notebook is preserved for historical reference but no longer drives the pipeline.
- **`reports/` for project history**: one Markdown file per phase, committed to the repo. Six months from now, anyone can read these and reconstruct what was tried, why, and what it produced.

---

## 4. Key Design Decisions

### 4.1 Model artifact = `.joblib` + `.json` metadata bundle

A pickled model alone is unusable. The metadata file stores everything needed to interpret and audit a model:

```json
{
  "trained_at": "2026-05-01T12:56:52.208947Z",
  "data_hash": "b14863b93374",
  "raw_train_hash": "f6e4597c142d",
  "raw_store_hash": "f56bd124a284",
  "feature_columns": [...],
  "split_date": "2015-01-30",
  "model_params": {...},
  "metrics": {...},
  "seed": 42
}
```

This is the seed of what becomes a **model registry** in Phase 9. Even at this stage, the artifact is no longer a black box: schema, hyperparameters, training data, and metrics are all recoverable.

### 4.2 Switched from `pickle` to `joblib`

`joblib` is the sklearn-recommended serialization format. It handles large numpy arrays more efficiently and is the standard across the sklearn ecosystem. Functionally similar to `pickle`, but the right tool for the job.

### 4.3 Time-aware split moved into the pipeline

The Phase 1 honest split was a one-off cell. In Phase 2, `time_aware_split` is a function in `src/data.py` and is called by `train.py` every run. The temporal leakage sin from Phase 1 is now structurally impossible — there is no `train_test_split` import anywhere in the project.

### 4.4 Hyperparameters tightened

Phase 1 used `n_estimators=50` with unlimited depth — a model prone to overfitting and slow to predict. Phase 2 uses:

```yaml
n_estimators: 100
max_depth: 15
min_samples_leaf: 5
```

This produced a higher MAE on the single time-aware test period (1059 vs Phase 1's 785), but a smaller, more constrained model that is more honest about what it can generalize. **Whether it is actually "better" cannot be answered with a single number** — that is the explicit subject of Phase 3 (cross-validation).

### 4.5 Data versioning via hashing

Three hashes are recorded in the metadata:
- `raw_train_hash` — SHA256 of `train.csv`
- `raw_store_hash` — SHA256 of `store.csv`
- `data_hash` — hash of the cleaned, post-merge dataframe

If any of these change, the model trained from them is provably different. This is the lightweight version of what DVC does for full data versioning, and it is enough for this project's needs.

---

## 5. Git Setup

The project now lives on GitHub at https://github.com/MarcoAlikhani/Rossmann-forecast with the following hygiene in place:

- `.gitignore` covers `venv/`, `data/raw/`, `data/processed/`, `models/*` (with `.gitkeep` exception), `__pycache__`, `.env`, IDE folders, and OS junk
- README documents setup, training, structure, and roadmap
- Commits are scoped per logical change with descriptive messages
- Repository is public — visible as portfolio work

### Lesson learned mid-phase

The first push committed `models/forecast_model_metadata.json` because the original `.gitignore` only ignored `*.pkl` and `*.joblib`, not `*.json`. Fixed by changing the rule to `models/*` + `!models/.gitkeep` and using `git rm --cached` to untrack the leaked file.

**General principle reinforced:** ignore *containers* (folders for generated artifacts), not specific *file types* inside them. New artifact formats can appear; the ignore rule should not have to be updated each time.

The leaked file will remain in old commit history. For a learning project with non-sensitive metadata, this is acceptable. In production, a secret leak would require history rewriting (`git filter-repo` or BFG) and rotation of the leaked credential — a much harder cleanup than preventing the commit in the first place.

---

## 6. Results

### 6.1 Training run (Phase 2)

```
Loaded 1,017,209 rows
Cleaned data hash: b14863b93374
Split at 2015-01-30 → train: 674,844, test: 169,494
MAE: 1059.16
Baseline (mean) MAE: 2269.30
Lift over mean: 53.3%
```

### 6.2 Model comparison across phases

| Run | Setup | MAE | Notes |
|---|---|---|---|
| Phase 1 random split | RF(50, no depth limit) | 815.66 | Leaky split — number unreliable |
| Phase 1 honest split | RF(50, no depth limit) | 784.85 | Single-period score, lucky |
| Phase 2 | RF(100, depth=15, min_leaf=5) | 1059.16 | Constrained model, single-period score |

The naive comparison says "Phase 2 is worse." The correct interpretation is: **single-period evaluation is unreliable**, regardless of which way it goes. Phase 3 will replace this with multi-fold time-series cross-validation, after which "better" and "worse" can be claimed with statistical confidence.

### 6.3 Reproducibility check

Running `python train.py` twice in succession produces:
- ✅ Identical `data_hash`
- ✅ Identical `mae` to all decimal places
- ✅ Identical feature column order

The pipeline is bit-for-bit deterministic given the same inputs. This is the property that makes everything downstream possible.

---

## 7. Sins Closed in Phase 2

From the Phase 1 inventory (22 sins total):

- ✅ #1 Hardcoded file paths → moved to `configs/config.yaml`
- ✅ #2 No project structure → proper `src/` package layout
- ✅ #3 Cells out of order, hidden state → linear `train.py` script
- ✅ #4 Dependencies not pinned → `requirements.txt` with exact versions
- ✅ #5 No `.gitignore`, no git history → repo on GitHub with clean history
- ✅ #6 No data versioning → SHA256 hashes in metadata bundle

Bonus: #19 (model artifact has no metadata) is partially closed — metadata exists but there is no central registry yet. Full closure in Phase 9.

**Remaining: 16 sins.** The next four (Phase 3) close validation-related sins.

---

## 8. Artifacts Produced

| File | Purpose | In git? |
|---|---|---|
| `configs/config.yaml` | All knobs in one place | ✅ |
| `requirements.txt` | Pinned dependencies | ✅ |
| `src/data.py` | Data loading, preprocessing, time split, hashing | ✅ |
| `src/features.py` | X/y construction | ✅ |
| `src/model.py` | Train + evaluate functions | ✅ |
| `train.py` | One-command pipeline | ✅ |
| `.gitignore` | Hygiene | ✅ |
| `README.md` | Project overview | ✅ |
| `models/forecast_model.joblib` | Trained model | ❌ (gitignored) |
| `models/forecast_model_metadata.json` | Model schema + metrics + hashes | ❌ (gitignored) |

---

## 9. Key Takeaways

1. **Reproducibility is engineering, not science.** None of the changes in Phase 2 made the model better. They made the model *trustable*. That distinction is the whole point of MLOps.
2. **A single MAE number is still meaningless.** Phase 2 produced a different number from Phase 1, and neither is "right." This is a feature — the project is now honest about its uncertainty, which sets up Phase 3 to address it properly.
3. **Configuration belongs outside code.** Every hardcoded number that became a config entry is one fewer reason to edit code in production. This is also what makes Phase 6 (CI/CD with environment-specific configs) possible later.
4. **Ignore folders, not file types.** The metadata leak was a small reminder that `.gitignore` rules should target *containers* of generated artifacts, with explicit exceptions for what should remain (like `.gitkeep`).
5. **Git is for code, not artifacts.** Models, data, and processed outputs do not belong in git. Phase 9 will introduce a proper registry; for now, gitignore is the right tool.

---

## 10. Next Phase

**Phase 3 — Validation & Tests.** Add `pytest` unit tests for preprocessing and feature logic, schema validation for incoming data (with `pandera` or similar), and proper time-series cross-validation that reports MAE across multiple time folds with a mean and standard deviation. The goal: any future change to `src/` or `configs/` must pass tests before being merged. The project becomes self-defending.
