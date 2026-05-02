"""Pydantic schemas — request/response contracts for the API."""

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """One prediction input. Mirrors INFERENCE_INPUT_SCHEMA from Phase 3."""

    Store: int = Field(..., gt=0, description="Store ID")
    DayOfWeek: int = Field(..., ge=1, le=7, description="1=Mon ... 7=Sun")
    Open: int = Field(..., ge=0, le=1, description="1 if store is open")
    Promo: int = Field(..., ge=0, le=1, description="1 if running a promo")
    SchoolHoliday: int = Field(..., ge=0, le=1)
    CompetitionDistance: float = Field(0.0, ge=0)
    CompetitionOpenSinceMonth: float = Field(0.0, ge=0, le=12)
    CompetitionOpenSinceYear: float = Field(0.0)
    Promo2: int = Field(0, ge=0, le=1)
    Promo2SinceWeek: float = Field(0.0, ge=0, le=53)
    Promo2SinceYear: float = Field(0.0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "Store": 1,
                    "DayOfWeek": 4,
                    "Open": 1,
                    "Promo": 1,
                    "SchoolHoliday": 0,
                    "CompetitionDistance": 1270.0,
                    "CompetitionOpenSinceMonth": 9.0,
                    "CompetitionOpenSinceYear": 2008.0,
                    "Promo2": 0,
                    "Promo2SinceWeek": 0.0,
                    "Promo2SinceYear": 0.0,
                }
            ]
        }
    }


class BatchPredictionRequest(BaseModel):
    """Batch of inputs."""

    inputs: list[PredictionRequest]


class PredictionResponse(BaseModel):
    """One prediction output."""

    predicted_sales: float


class BatchPredictionResponse(BaseModel):
    """Batch of outputs, plus model version info."""

    predictions: list[PredictionResponse]
    model_version: str  # data_hash from training
    trained_at: str


class HealthResponse(BaseModel):
    """Liveness + model load status."""

    status: str
    model_loaded: bool
    model_version: str | None = None
