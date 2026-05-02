# Phase 5 Report — Local Deployment Polish

**Project:** Rossmann Store Sales Forecasting
**Phase:** 5 of 12 — Make the service observable, debuggable, operationally sound
**Date:** 2026-05-02
**Status:** ✅ Complete
**Repo:** https://github.com/MarcoAlikhani/Rossmann-forecast

---

## 1. Objective

Phase 4 delivered a working API. Phase 5 makes that API **operable**: every request must be traceable, every log line must be machine-parseable, every endpoint must be measured, and the service's true capacity must be characterized — not guessed.

The success criterion: an SRE on call at 3am, who has never seen this service, must be able to answer "what is happening right now?" using only logs and metrics, without reading source code.

---

## 2. The Six Properties of an Operable Service

| # | Property | Phase 4 status | Phase 5 status |
|---|---|---|---|
| 1 | Every request has a unique ID | ❌ | ✅ UUID per request, echoed in `X-Request-ID` header |
| 2 | Logs are structured (JSON) | ❌ Plain strings | ✅ structlog JSON output, contextvars-bound |
| 3 | In-process metrics endpoint | ❌ | ✅ `/metrics` in Prometheus format |
| 4 | Cold-start latency mitigated | ❌ First request 400ms+ | ✅ Warmup at startup, first request <50ms |
| 5 | Capacity is characterized, not guessed | ❌ One load test point | ✅ Multi-step ramp identifying breakdown point |
| 6 | All new behavior is tested | ❌ | ✅ 3 new tests covering middleware + metrics |

All six now pass.

---

## 3. What Was Built

### 3.1 Structured logging (`api/logging_config.py`)

Replaced Python's stdlib `logging.basicConfig(format="...")` with **structlog** configured to emit JSON. Every log line is now a parseable object with:

- `event` — the log message (e.g. `"prediction_made"`)
- `level` — `info`, `warning`, `error`
- `timestamp` — ISO-8601 with timezone
- `request_id`, `method`, `path` — auto-bound via `contextvars` middleware
- Arbitrary domain fields — `store`, `predicted_sales`, `duration_s`, etc.

Why this matters: in production, logs flow into aggregators (Datadog, Splunk, ELK, CloudWatch). Plain text requires regex parsing — fragile, slow, often silently wrong. JSON logs are queryable like a database. *"Show me all 5xx errors for store=42 in the last hour"* becomes a one-line query.

### 3.2 Request context middleware (`api/middleware.py`)

A `BaseHTTPMiddleware` that runs on every request and:

1. **Generates or accepts a request ID.** Clients can pass `X-Request-ID` for distributed tracing; otherwise the server generates a UUID.
2. **Binds context for the request lifetime.** `request_id`, `method`, and `path` get attached to every log line emitted while the request is in flight via structlog's `contextvars`.
3. **Logs request lifecycle.** Emits `request_started` and `request_completed` events with duration.
4. **Records Prometheus metrics.** Increments a counter labeled by method/endpoint/status, observes the duration on a histogram.
5. **Echoes the request ID in the response header.** So the calling client also has the trace key.

The result: a single prediction request now produces three correlated log lines, all sharing the same `request_id`, plus metric increments. An operator can pluck one ID from anywhere — a user's bug report, an alert, a slow query — and reconstruct the entire request.

### 3.3 Prometheus metrics endpoint (`/metrics`)

Three metrics families exposed:

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `forecast_api_requests_total` | Counter | method, endpoint, status_code | Traffic volume per endpoint, error rates |
| `forecast_api_request_duration_seconds` | Histogram | method, endpoint | Latency distribution; powers p50/p95/p99 |
| `forecast_api_predictions_total` | Counter | endpoint | Total predictions made (single + batch) |

The `/metrics` endpoint is plain text in the Prometheus exposition format. Phase 10 will scrape it from Prometheus and visualize in Grafana. The point of doing this *now* (instead of Phase 10) is that the instrumentation lives next to the code it instruments — adding it in a later phase would mean revisiting every endpoint.

### 3.4 Startup warmup

Random Forest models have a cold-start cost on the first prediction: the trees are deserialized lazily, CPU caches are cold, sklearn initializes some internal state. On this 77MB model, the first prediction takes ~400ms; subsequent ones take ~30-50ms.

The fix: a `_warmup_model()` call inside the `lifespan` startup, which runs a dummy prediction with the correct feature schema. By the time the first real client request arrives, all caches are warm and the model is fully resident.

### 3.5 New tests

Three tests added to `tests/test_api.py`:

- `test_metrics_endpoint_exposes_prometheus_format` — `/metrics` returns text, contains the expected metric names
- `test_request_id_echoed_in_response` — client-supplied `X-Request-ID` flows through
- `test_request_id_generated_when_missing` — server generates a UUID if client omits

Total project tests after Phase 5: **21**, all passing in under 5 seconds.

---

## 4. Results

### 4.1 Logs are now structured and traceable

A single prediction request produces three correlated log lines:

```json
{"event": "request_started", "path": "/predict", "request_id": "3233ed4c-50cf-4a74-ac55-a9473425bf42", "method": "POST", "level": "info", "timestamp": "2026-05-02T15:31:41.150377Z"}
{"store": 1, "day_of_week": 4, "predicted_sales": 5359.84, "event": "prediction_made", "request_id": "3233ed4c-50cf-4a74-ac55-a9473425bf42", "level": "info", "timestamp": "2026-05-02T15:31:41.183376Z"}
{"status_code": 200, "duration_s": 0.0339, "event": "request_completed", "request_id": "3233ed4c-50cf-4a74-ac55-a9473425bf42", "level": "info", "timestamp": "2026-05-02T15:31:41.184384Z"}
```

A grep for one `request_id` returns the entire request lifecycle. The prediction value, the inputs, the latency (33.9ms here), the HTTP outcome — all linked.

### 4.2 Capacity test results

A four-step ramp test was run on the 8-worker container, 2 minutes per step:

| Concurrent users | Median /predict | 95%ile /predict | 99%ile /predict | RPS | Failures |
|---|---|---|---|---|---|
| 10 | 75ms | 130ms | 160ms | ~25 | 0 |
| 50 | 75ms | 130ms | 160ms | ~25* | 0 |
| 100 | 78ms | 150ms | 200ms | 119 | 0 |
| 200 | 210ms | 630ms | 860ms | 155 | 0 |

*The 50-user run was throughput-limited by Locust's wait-time configuration (0.1–0.5s think time per user), not by the service.

### 4.3 The capacity curve and what it reveals

The curve has three distinct regions:

**Linear region (10 → 100 users).** Median latency is essentially flat at ~75-78ms while throughput scales from ~25 to 119 RPS. The 8 workers have spare capacity; each new user is served at the same speed as the last. This is the **operational sweet spot**.

**The knee (100 → 200 users).** Median jumps 78ms → 210ms (2.7×). 95%ile explodes 150ms → 630ms (4.2×). 99%ile goes 200ms → 860ms (4.3×). The 8 workers are saturated; requests queue. Queue depth grows non-linearly with user count, which is exactly why tail latency degrades worst.

**Past the knee (200+ users).** Not measured, but extrapolating: latency continues climbing while RPS plateaus and eventually drops as the system spends more time on queue management than work.

### 4.4 Operational profile defined

The capacity test produced a defensible service profile:

- **Up to ~100 concurrent users**: median <100ms, 99%ile <250ms. Production-grade for user-facing traffic.
- **100–200 users**: works without failures, degrades gracefully. Acceptable for batch workflows or internal tools.
- **>200 users**: scale out (more replicas, more workers) or swap to a lighter model (LightGBM ~5–10× faster than Random Forest at inference).

This is what capacity planning looks like in real engineering: SLAs are measured, not promised.

---

## 5. Implications for Phase 7 (Cloud Deployment)

The capacity curve directly drives cloud sizing decisions:

- **One container** at this configuration handles ~100 concurrent users at <100ms median.
- A traffic forecast of 300 concurrent users → **3 replicas** behind a load balancer.
- A traffic forecast of 500 → **5 replicas**, or swap RF for a lighter model and stay at 2-3 replicas.
- Memory budget per replica: 8 workers × ~80MB model = ~640MB minimum, plus ~200MB Python overhead. Round to 1GB per container.

Without Phase 5, these numbers would be guesses. With Phase 5, they are derived from measurement.

---

## 6. Sins Closed in Phase 5

From the Phase 1 inventory:

- ✅ #18 (partial) No structured logging or metrics → JSON logs + `/metrics` endpoint
  - Phase 8 will complete the rest (centralized log shipping, alerting)

**1 sin closed (partial). 6 remaining.** Phases 6–8 close CI/CD and remaining deployment/observability sins.

---

## 7. Updated Project Structure

```
rossmann-forecast/
├── api/
│   ├── __init__.py
│   ├── logging_config.py       # NEW — structlog JSON setup
│   ├── main.py                 # +middleware, +warmup, +/metrics
│   ├── middleware.py           # NEW — request IDs + Prometheus metrics
│   └── schemas.py
├── configs/
├── data/
├── loadtest/
│   └── locustfile.py
├── models/
├── notebooks/
├── reports/
│   ├── phase_01_the_sin.md
│   ├── phase_02_reproducibility.md
│   ├── phase_03_validation_and_tests.md
│   ├── phase_04_api_and_containerization.md
│   └── phase_05_local_deployment_polish.md
├── src/
├── tests/
│   ├── test_api.py             # +3 tests for new behavior
│   ├── test_data.py
│   ├── test_features.py
│   └── test_model.py
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
├── requirements.txt            # +structlog, prometheus-client, python-json-logger
└── train.py
```

Two new modules, three new tests, one updated `main.py`. The structural footprint of "becoming operable" was small. The behavioral change is large.

---

## 8. Key Design Decisions

### 8.1 structlog over Python's stdlib logging

Python's stdlib `logging` is string-formatter-based: every log call constructs a string. To emit structured fields you'd need `extra={...}` dicts, which most code forgets to use, and which still don't compose well across function boundaries. structlog flips the model: log calls accept keyword arguments natively, and processors transform the dict into JSON at output. Adding context (`request_id`, `model_version`) is a one-liner. This pays off most when logs are aggregated: dashboards filter on fields, not regex.

### 8.2 contextvars for request scoping

`structlog.contextvars.bind_contextvars(request_id=...)` ensures every log line emitted *during* the request automatically carries the request ID — no need to pass it explicitly through every function call. This works cleanly with FastAPI's async model because contextvars are async-safe. Trying to do the same with thread-locals would break the moment the code touched any async path.

### 8.3 Prometheus over a custom metrics format

Custom JSON-over-HTTP metrics endpoints are tempting but a dead end: every monitoring system would need a custom integration. Prometheus's exposition format is the de facto standard — supported by Datadog, Grafana Cloud, AWS, GCP, every Kubernetes setup. Emitting it from day one means the Phase 10 monitoring infrastructure is plug-and-play.

### 8.4 Warmup is part of `lifespan`, not a request handler

The warmup is run *during startup*, before the server starts accepting traffic. An alternative — warmup on first request — would still hit one user with the cold path. Doing it inside `lifespan` means the first real request is fast for everyone. The cost: the container takes ~1 second longer to start. Worth it.

### 8.5 Multi-step ramp instead of one big load test

A single 50-user test at peak gave us the average latency, but not the *shape* of the curve. The 100-user knee point and the 200-user degradation would have been invisible without testing each level explicitly. Capacity planning is about finding inflection points, not summary statistics.

---

## 9. Key Takeaways

1. **Logs without request IDs are not really logs — they are noise.** A single request produces N log lines; without correlation, debugging becomes archaeological. The middleware that binds `request_id` is 30 lines of code and pays for itself the first time something breaks at 3am.
2. **JSON logs are not "nice to have" — they are the price of admission for production.** Plain text logs cannot be filtered efficiently, cannot be aggregated meaningfully, cannot drive alerting. Every minute spent retrofitting JSON logs after the fact is a minute that could have been one line of structlog config up front.
3. **Capacity is a curve, not a number.** "How many users can the service handle?" is a meaningless question. "At what concurrency does median latency cross 100ms?" is meaningful. The shape of the latency-vs-concurrency curve dictates every downstream sizing decision.
4. **The metrics you don't emit, you cannot measure.** Adding the `/metrics` endpoint cost effectively nothing in this phase, but adding it after Phase 10 (when we'd want dashboards) would mean revisiting every endpoint. Instrument as you build, not after.
5. **An operable service is not a sophisticated service.** Phase 5 added zero ML capability. It added the ability to *see* what the service is doing — which is what makes the difference between "runs on my laptop" and "an SRE can keep this alive in production."

---

## 10. Next Phase

**Phase 6 — CI/CD.** Wire GitHub Actions to run the full test suite on every push, build the Docker image on every merge to main, and (optionally) push the image to GitHub Container Registry. The goal: no untested code can be merged, no manual builds happen ever again. Every commit becomes a candidate for deployment automatically.
