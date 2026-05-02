# Phase 4 Report — API & Containerization

**Project:** Rossmann Store Sales Forecasting
**Phase:** 4 of 12 — Model becomes a callable network service
**Date:** 2026-05-02
**Status:** ✅ Complete
**Repo:** https://github.com/MarcoAlikhani/Rossmann-forecast

---

## 1. Objective

Transform the trained model from a static `.joblib` file on disk into a **production-grade HTTP service** that:

- Accepts requests over the network with validated inputs
- Returns structured JSON responses
- Reports its own health to orchestrators and load balancers
- Runs identically on any Linux/Mac/Windows machine via Docker
- Survives concurrent load with measured, defensible latency

The success criterion: a remote client can `POST /predict` and receive a forecast in under 200ms median, with zero failures, while 50 concurrent users hit the service.

---

## 2. The Six Properties of a Servable Model

| # | Property | Phase 3 status | Phase 4 status |
|---|---|---|---|
| 1 | Runs as a process, not a script | ❌ Run-and-exit `train.py` | ✅ Persistent uvicorn ASGI server |
| 2 | Inputs validated before reaching model | ❌ Trust the caller | ✅ Pydantic schemas reject bad input with HTTP 422 |
| 3 | Outputs structured (JSON, predictable schema) | ❌ Print to stdout | ✅ `response_model` enforces shape on every endpoint |
| 4 | Health endpoint | ❌ | ✅ `/health` reports model load status, version |
| 5 | Portable across machines | ❌ Local venv-dependent | ✅ Docker image, layer-cached, non-root |
| 6 | Latency measured, not assumed | ❌ | ✅ Locust load tests, before/after metrics |

All six now pass.

---

## 3. What Was Built

### 3.1 The API service (`api/`)

A FastAPI application with three endpoints:

- **`GET /health`** — liveness + model load status. Used by Docker's `HEALTHCHECK` directive and by future load balancers (k8s, ECS, Fly.io).
- **`POST /predict`** — single prediction. Returns `{predicted_sales: float}`.
- **`POST /predict/batch`** — multi-row prediction. Returns predictions plus model version metadata. Batch endpoints exist because they amortize per-call overhead and are dramatically more efficient than N parallel single calls.

### 3.2 Lifespan-managed model loading

The model is loaded **once** at server startup via FastAPI's `lifespan` context manager, not on every request. Loading the 77MB model takes roughly one second; doing this per-request would push latency from 50ms into the seconds. The lifespan pattern is the modern, standard way to handle one-time initialization in async Python services.

### 3.3 Pydantic boundary validation (`api/schemas.py`)

Every request is parsed and validated by Pydantic *before* it reaches handler code. Field-level constraints (`Store > 0`, `DayOfWeek in 1..7`, `Open in 0..1`) reject malformed inputs with a detailed HTTP 422 response. The model code never sees garbage.

This mirrors the `INFERENCE_INPUT_SCHEMA` defined in Phase 3 — Pydantic is the runtime enforcement at the API boundary, pandera is the runtime enforcement inside the training pipeline. Same defensive pattern, two layers.

### 3.4 Auto-generated OpenAPI docs

Because the schemas are declarative, FastAPI generates an interactive `/docs` page automatically. Anyone (including future-you in 6 months) can visit `http://localhost:8000/docs`, see the full API contract, and try requests without writing client code. This is documentation that cannot drift from reality — it is generated from the same code that enforces validation.

### 3.5 Containerization (`Dockerfile`, `docker-compose.yml`)

The Dockerfile is structured for production hygiene:

- **Pinned base image** (`python:3.10-slim`) — no `latest` tag, no surprise upgrades
- **Layer-optimized** — `requirements.txt` copied and installed *before* application code, so dependency installation is cached when only code changes (rebuilds drop from ~4 minutes to ~10 seconds)
- **Non-root user** — `appuser` created and used, so a process compromise doesn't grant root inside the container
- **`HEALTHCHECK` directive** — Docker hits `/health` periodically and marks the container unhealthy if it stops responding; orchestrators use this to drive auto-restart and traffic routing

`docker-compose.yml` provides the one-command startup interface. Phase 5 will add a load-test container; Phase 10 will add Prometheus and Grafana sidecars. Compose scales naturally as the system grows.

### 3.6 API tests (`tests/test_api.py`)

Five new tests using FastAPI's `TestClient`:

- `test_health_returns_ok` — the contract of `/health`
- `test_predict_returns_number` — happy-path prediction works
- `test_predict_rejects_invalid_input` — Pydantic catches `DayOfWeek=99`
- `test_predict_rejects_missing_field` — Pydantic catches missing required fields
- `test_predict_batch_returns_list` — batch endpoint returns the right shape

Total project test count after Phase 4: **18 tests**, all passing in under 5 seconds.

### 3.7 Load testing (`loadtest/locustfile.py`)

A Locust user class that simulates realistic mixed traffic: 10 prediction calls per 1 health call, with 0.1–0.5 second think time between calls. This is the artifact that turned an assumption ("the API is probably fast enough") into a measurement.

---

## 4. Results

### 4.1 The first load test exposed a hidden disaster

Initial run: 50 concurrent users, default uvicorn (1 worker).

| Endpoint | Median | 95%ile | 99%ile | RPS |
|---|---|---|---|---|
| GET /health | 550ms | 870ms | 1000ms | 3.3 |
| POST /predict | 1200ms | 1700ms | 1800ms | 28.2 |

**These numbers were unacceptable.** A static health check returning a dict had no business taking half a second. The article's "API must respond under 120ms" line was now a real, measured failure of this service.

### 4.2 Diagnosis: it was never the model

Sequential probing (one request at a time, no concurrency) showed:

- `/health` — 2-6ms (excellent)
- `/predict` — 50ms after first-request warmup (acceptable)

The model and the framework were both fine. The single-thread latency was within target. **The bottleneck was concurrency, not computation.**

A single uvicorn worker has one Python event loop. Random Forest predictions are CPU-bound and hold the GIL. Under 50 concurrent users, requests queued behind each other inside that one process. Even `/health` — which never touches the model — was queued behind in-flight prediction work.

### 4.3 The fix: multi-worker uvicorn

One configuration change: `--workers 8` in the Dockerfile CMD, exposed via the `WORKERS` environment variable for per-environment tuning. Each worker is its own process, with its own copy of the model in memory, served in parallel by the OS kernel.

### 4.4 The second load test

Same 50-user, 5/sec ramp, 8 workers.

| Endpoint | Median | 95%ile | 99%ile | RPS |
|---|---|---|---|---|
| GET /health | 16ms | 59ms | 110ms | 8.2 |
| POST /predict | 140ms | 340ms | 500ms | 103.5 |

### 4.5 Before / after summary

| Metric | 1 worker | 8 workers | Improvement |
|---|---|---|---|
| /predict median | 1200ms | 140ms | **8.6× faster** |
| /predict 95%ile | 1700ms | 340ms | 5.0× faster |
| /predict RPS | 28.2 | 103.5 | **3.7× throughput** |
| /health median | 550ms | 16ms | 34× faster |
| Failed requests | 0 | 0 | ✅ |

**One configuration line. 8× latency reduction. Zero code changes.** The model, image, and dependencies were unchanged.

### 4.6 Interpretation

The post-fix numbers place the service in the **"good" tier** for ML inference latency:

| Tier | Range | Status |
|---|---|---|
| Excellent | <50ms | (single-request latency lives here) |
| **Good** | **50–200ms** | **/predict median 140ms** ✅ |
| Acceptable | 200–500ms | (95%ile-99%ile lives here) |
| Red flag | >500ms | not reached at this load |

The service can serve real production traffic. The remaining tail latency (95%ile = 340ms, 99%ile = 500ms) is the natural queueing effect of 50 users sharing 8 workers — improvable with more workers, a smaller model (e.g. swap RF for LightGBM in a later phase), or horizontal scaling.

---

## 5. The Cardinal Lesson of Phase 4

> **Throughput and latency under concurrency are not properties of the model. They are properties of the system architecture.**

This is the central insight the original article was pointing at. Data scientists optimize loss; engineers optimize concurrent system behavior. The same model can be unusable or production-grade depending purely on how the serving layer is configured. There was no algorithmic improvement, no quantization, no hardware change between the two load tests — only a worker count.

This is also why "MAE 1092 in CV" alone never determined whether the project could ship. A model is half the system. The other half is the boundary, the workers, the container, the orchestrator, the queue, the health check, the load test. **Phase 4 made all of those exist.**

---

## 6. Sins Closed in Phase 4

From the Phase 1 inventory (22 total sins):

- ✅ #12 No API, no service interface → FastAPI service with three endpoints
- ✅ #13 No input validation at inference → Pydantic schemas at the boundary
- ✅ #14 No containerization → Dockerfile + docker-compose, layer-optimized, non-root
- ✅ #15 No latency measurement → Locust load tests run and analyzed

**4 sins closed this phase. 7 remaining.** Phases 5–8 close deployment and observability sins; phases 9–12 close registry, monitoring, drift, and retraining.

---

## 7. Updated Project Structure

```
rossmann-forecast/
├── api/                         # NEW
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan model loading
│   └── schemas.py               # Pydantic request/response contracts
├── configs/
│   └── config.yaml
├── data/
│   ├── raw/                     # gitignored
│   └── processed/
├── loadtest/                    # NEW
│   └── locustfile.py            # 50-user prediction load test
├── models/                      # gitignored
├── notebooks/
│   └── 01_exploration.ipynb
├── reports/
│   ├── phase_01_the_sin.md
│   ├── phase_02_reproducibility.md
│   ├── phase_03_validation_and_tests.md
│   └── phase_04_api_and_containerization.md
├── src/
│   ├── data.py
│   ├── features.py
│   ├── model.py
│   └── schema.py
├── tests/
│   ├── test_api.py              # NEW — 5 API tests
│   ├── test_data.py
│   ├── test_features.py
│   └── test_model.py
├── .dockerignore                # NEW
├── .gitignore
├── Dockerfile                   # NEW
├── docker-compose.yml           # NEW
├── README.md
├── requirements.txt             # +fastapi, uvicorn, pydantic, httpx, locust
└── train.py
```

---

## 8. Key Design Decisions

### 8.1 Lifespan over global model variable

Loading the model in a module-level statement (e.g. `model = joblib.load(...)` at the top of `main.py`) is a common anti-pattern. It runs at import time, before logging is configured, before the app is ready, and provides no clean shutdown. The `lifespan` context manager loads at startup, after the app is wired up, and is the documented, supported pattern. Use it.

### 8.2 Workers count via environment variable

The Dockerfile sets `ENV WORKERS=8` and the CMD reads `$WORKERS`, so different deployments can use different worker counts without rebuilding the image. This is the [12-factor app](https://12factor.net/config) configuration principle: configuration in environment, not in code or rebuilt artifacts. Critical for Phase 7 (cloud deployment), where production and staging will have different resource profiles.

### 8.3 Batch endpoint included from day one

`POST /predict/batch` exists alongside `POST /predict`. Batch inference is dramatically more efficient than N parallel single calls because the model's per-call overhead is amortized across rows. Even though no current consumer uses it, it costs almost nothing to implement now and is much harder to add later once clients depend on the single endpoint shape. This is "design for the API you will need" — common production wisdom.

### 8.4 Schema separation: pandera in training, Pydantic in serving

Pandera is the right tool for validating dataframes inside the training pipeline. Pydantic is the right tool for validating individual JSON payloads at the API boundary. They overlap conceptually but serve different runtimes. Trying to use one tool in both places creates awkward fits in either one. Use both.

### 8.5 Model version exposed in responses

`/predict/batch` returns `model_version` (the data hash) and `trained_at`. This is the seed of model traceability — every prediction can be traced to the exact model that produced it. In Phase 9 (Model Registry) this gets formalized; in Phase 10 (Monitoring) this becomes how prediction-quality metrics are split per model version.

---

## 9. Key Takeaways

1. **Single-request latency is not production latency.** A model that responds in 50ms when probed sequentially can take 1200ms under concurrent load. Measure under load, not in isolation.
2. **Diagnosis beats guessing.** "The model is slow, let me try a different model" is the wrong reaction to a load-test failure. Sequential probing isolates the model from the system; the difference between the two reveals the actual bottleneck. In this case the model was innocent.
3. **One configuration change beat any algorithmic change.** Going from 1 to 8 uvicorn workers improved median latency by 8.6× without touching the model. Architecture decisions dominate model decisions for latency.
4. **The boundary deserves as much rigor as the model.** Pydantic schemas, structured responses, OpenAPI docs, health checks, container hygiene — none of these affect prediction quality, all of them affect whether the service can be run at all.
5. **Docker layer caching is non-negotiable.** A 4-minute build that drops to 10 seconds on cached layers is the difference between iterating fast and iterating never. Copying `requirements.txt` first, before code, is the single highest-leverage Dockerfile pattern.

---

## 10. Next Phase

**Phase 5 — Local Deployment Polish.** Tighten what Phase 4 built before pushing to the cloud. Add structured request logging, request IDs, basic in-process metrics (request counts, latency histograms), graceful shutdown handling, and a "warmup" call at startup so the first real request isn't slow. Replicate the load test under more realistic conditions (longer duration, different user counts) to characterize capacity. The output of Phase 5 is a service that is ready, in every observable sense, to be exposed to the public internet — which Phase 6 (CI/CD) and Phase 7 (cloud deployment) then do.
