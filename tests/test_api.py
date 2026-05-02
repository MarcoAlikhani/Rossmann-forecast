"""Tests for the FastAPI service."""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    """Test client — uses the lifespan context, so model loads at fixture setup."""
    with TestClient(app) as c:
        yield c


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_version"] is not None


def test_predict_returns_number(client):
    payload = {
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
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    assert "predicted_sales" in r.json()
    assert r.json()["predicted_sales"] > 0


def test_predict_rejects_invalid_input(client):
    """Pydantic should reject DayOfWeek=99."""
    payload = {
        "Store": 1,
        "DayOfWeek": 99,
        "Open": 1,
        "Promo": 0,
        "SchoolHoliday": 0,
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 422  # validation error


def test_predict_rejects_missing_field(client):
    """Missing required field must be rejected."""
    payload = {"Store": 1}
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_predict_batch_returns_list(client):
    payload = {
        "inputs": [
            {"Store": 1, "DayOfWeek": 4, "Open": 1, "Promo": 1, "SchoolHoliday": 0,
             "CompetitionDistance": 1270.0, "CompetitionOpenSinceMonth": 9.0,
             "CompetitionOpenSinceYear": 2008.0, "Promo2": 0,
             "Promo2SinceWeek": 0.0, "Promo2SinceYear": 0.0},
            {"Store": 2, "DayOfWeek": 5, "Open": 1, "Promo": 0, "SchoolHoliday": 0,
             "CompetitionDistance": 570.0, "CompetitionOpenSinceMonth": 11.0,
             "CompetitionOpenSinceYear": 2007.0, "Promo2": 1,
             "Promo2SinceWeek": 13.0, "Promo2SinceYear": 2010.0},
        ]
    }
    r = client.post("/predict/batch", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 2
    assert body["model_version"] is not None