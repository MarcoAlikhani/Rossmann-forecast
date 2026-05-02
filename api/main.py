"""FastAPI application — serves the forecast model."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
import structlog
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.logging_config import configure_logging
from api.middleware import (
    PREDICTION_COUNT,
    RequestContextMiddleware,
)
from api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
)

configure_logging("INFO")
logger = structlog.get_logger("forecast-api")

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "forecast_model.joblib"
METADATA_PATH = ROOT / "models" / "forecast_model_metadata.json"

state: dict = {}


def _warmup_model(model, feature_cols: list):
    """Run a dummy prediction to warm up caches and JIT paths."""
    warmup_row = pd.DataFrame(
        [{col: 1.0 for col in feature_cols}],
        columns=feature_cols,
    )
    _ = model.predict(warmup_row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model at startup, run warmup, clean up at shutdown."""
    logger.info("lifespan_starting", model_path=str(MODEL_PATH))

    if not MODEL_PATH.exists():
        logger.error("model_file_not_found", path=str(MODEL_PATH))
        state["model"] = None
        state["metadata"] = None
        yield
        state.clear()
        return

    state["model"] = joblib.load(MODEL_PATH)
    with open(METADATA_PATH) as f:
        state["metadata"] = json.load(f)

    logger.info(
        "model_loaded",
        version=state["metadata"]["data_hash"],
        trained_at=state["metadata"]["trained_at"],
        n_features=len(state["metadata"]["feature_columns"]),
    )

    # Warmup — first real request is no longer slow
    try:
        _warmup_model(state["model"], state["metadata"]["feature_columns"])
        logger.info("warmup_complete")
    except Exception as exc:
        logger.warning("warmup_failed", error=str(exc))

    yield

    logger.info("lifespan_shutting_down")
    state.clear()


app = FastAPI(
    title="Rossmann Forecast API",
    description="Daily sales forecasting service",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok" if state.get("model") is not None else "degraded",
        model_loaded=state.get("model") is not None,
        model_version=state.get("metadata", {}).get("data_hash") if state.get("metadata") else None,
    )


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint — scraped by Prometheus in Phase 10."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    if state.get("model") is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feature_cols = state["metadata"]["feature_columns"]
    row = pd.DataFrame([req.model_dump()])[feature_cols]
    pred = float(state["model"].predict(row)[0])

    PREDICTION_COUNT.labels(endpoint="/predict").inc()
    logger.info("prediction_made", store=req.Store, day_of_week=req.DayOfWeek, predicted_sales=round(pred, 2))

    return PredictionResponse(predicted_sales=pred)


@app.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(req: BatchPredictionRequest):
    if state.get("model") is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feature_cols = state["metadata"]["feature_columns"]
    rows = pd.DataFrame([item.model_dump() for item in req.inputs])[feature_cols]
    preds = state["model"].predict(rows).tolist()

    PREDICTION_COUNT.labels(endpoint="/predict/batch").inc(len(preds))
    logger.info("batch_prediction_made", batch_size=len(preds))

    return BatchPredictionResponse(
        predictions=[PredictionResponse(predicted_sales=float(p)) for p in preds],
        model_version=state["metadata"]["data_hash"],
        trained_at=state["metadata"]["trained_at"],
    )