# Rossmann Store Sales Forecasting

End-to-end ML system for daily sales forecasting — built as a learning project to practice the full notebook → production journey.

## Project Status

🚧 In progress — currently at **Phase 2 of 12** (Reproducibility complete).

See `reports/` for phase-by-phase writeups.

## Setup

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows
# source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
```

## Data

Download `train.csv` and `store.csv` from the [Rossmann Store Sales Kaggle competition](https://www.kaggle.com/competitions/rossmann-store-sales/data) and place them in `data/raw/`.

## Train

```bash
python train.py
```

Produces `models/forecast_model.joblib` + `models/forecast_model_metadata.json`.

## Project Structure
.
├── configs/        # YAML configs (paths, hyperparameters)
├── data/raw/       # Raw CSVs (gitignored)
├── models/         # Trained model artifacts (gitignored)
├── notebooks/      # Exploration notebooks
├── reports/        # Phase-by-phase project reports
├── src/            # Source code (data, features, model)
├── tests/          # Unit + integration tests
└── train.py        # One-command training pipeline

## Roadmap

- [x] Phase 1: The Sin (deliberately bad notebook)
- [x] Phase 2: Reproducibility (project structure, configs, seeds)
- [ ] Phase 3: Validation & Tests
- [ ] Phase 4: API & Containerization
- [ ] Phase 5: Local Deployment
- [ ] Phase 6: CI/CD
- [ ] Phase 7: Cloud Deployment
- [ ] Phase 8: Logging & Metrics
- [ ] Phase 9: Model Registry
- [ ] Phase 10: Monitoring
- [ ] Phase 11: Drift Detection
- [ ] Phase 12: Retraining Pipeline