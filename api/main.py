"""FastAPI application — serves the forecast model."""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException

from api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
)

# Set up basic structured logging — Phase 8 will improve this
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("forecast-api")

# Resolve paths relative to this file, so it works whether run locally or in Docker
ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "forecast_model.joblib"
METADATA_PATH = ROOT / "models" / "forecast_model_metadata.json"

# Container for in-memory state — populated at startup, used by handlers
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model + metadata at startup; clear at shutdown."""
    logger.info("Loading model from %s", MODEL_PATH)
    if not MODEL_PATH.exists():
        logger.error("Model file not found at %s", MODEL_PATH)
        state["model"] = None
        state["metadata"] = None
    else:
        state["model"] = joblib.load(MODEL_PATH)
        with open(METADATA_PATH) as f:
            state["metadata"] = json.load(f)
        logger.info(
            "Model loaded. version=%s trained_at=%s",
            state["metadata"]["data_hash"],
            state["metadata"]["trained_at"],
        )
    yield
    state.clear()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Rossmann Forecast API",
    description="Daily sales forecasting service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health():
    """Liveness probe — used by Docker, k8s, load balancers."""
    return HealthResponse(
        status="ok" if state.get("model") is not None else "degraded",
        model_loaded=state.get("model") is not None,
        model_version=state.get("metadata", {}).get("data_hash") if state.get("metadata") else None,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    """Single prediction."""
    if state.get("model") is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feature_cols = state["metadata"]["feature_columns"]
    row = pd.DataFrame([req.model_dump()])[feature_cols]
    pred = float(state["model"].predict(row)[0])

    logger.info("predict store=%s day=%s -> %.2f", req.Store, req.DayOfWeek, pred)
    return PredictionResponse(predicted_sales=pred)


@app.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(req: BatchPredictionRequest):
    """Batch prediction — much more efficient than N separate calls."""
    if state.get("model") is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feature_cols = state["metadata"]["feature_columns"]
    rows = pd.DataFrame([item.model_dump() for item in req.inputs])[feature_cols]
    preds = state["model"].predict(rows).tolist()

    logger.info("predict_batch n=%d", len(req.inputs))
    return BatchPredictionResponse(
        predictions=[PredictionResponse(predicted_sales=float(p)) for p in preds],
        model_version=state["metadata"]["data_hash"],
        trained_at=state["metadata"]["trained_at"],
    )