"""Load test — measures real latency under concurrent load."""

from locust import HttpUser, between, task

SAMPLE_PAYLOAD = {
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


class ForecastUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(10)
    def predict(self):
        self.client.post("/predict", json=SAMPLE_PAYLOAD)

    @task(1)
    def health(self):
        self.client.get("/health")
