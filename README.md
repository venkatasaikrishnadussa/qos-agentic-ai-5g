## 5G Agentic Policy Optimizer – Overview

This service is a **FastAPI-based Agentic AI Policy Optimization System** for a simulated 5G Core network.  
It is designed to demonstrate how an operator could:

- Continuously **observe** telemetry from 5G core functions (UPF, SMF, AMF, NWDAF)
- Run **AI-driven reasoning** and policy simulation to optimize slice allocations
- Enforce policies through a **PCF (Policy Control Function) mock API**
- Track **SLA adherence** and decision quality via Prometheus metrics

### Problem Being Solved

Modern 5G networks expose multiple logical slices (eMBB, URLLC, mMTC, ENTERPRISE), each with different SLA targets and performance constraints.  
Operators want to:

- **Maximize network utilization** and revenue,
- While **maintaining strict SLAs** (e.g., URLLC latency, enterprise latency, reliability).

This project models an **agentic closed loop** that (in its full form) will:

1. Read streaming telemetry and congestion indicators.
2. Generate multiple candidate policy actions (e.g., adjust slice bandwidth allocations).
3. Simulate impact on latency/utilization and SLA violations.
4. Enforce safe actions through a guarded PCF API.
5. Continuously monitor results via metrics and logs.

At the moment, the REST API and PCF mock are wired up; the LangGraph agent loop is scaffolded in `app/runtime/loop.py` and can be extended.

---

## Project Layout

- `main.py` – FastAPI application entrypoint.
- `app/config` – Settings and configuration.
- `app/schemas` – Pydantic models for telemetry, policies, rewards, errors.
- `app/telemetry` – Telemetry simulator (async generator).
- `app/models` – ML congestion predictor (mock, pluggable).
- `app/simulation` – Policy simulation engine + guardrails.
- `app/pcf` – PCF mock API (REST) for policy enforcement.
- `app/observability` – Structured logging + Prometheus metrics.
- `app/runtime` – Closed-loop runner scaffolding.

---

## Running the Application

From the project root:

```bash
cd /Users/dussavenkatasaikrishna/Saikrishna/Python/DataScience/PhD/SecondSem/AIin5G/codebase/qos-agentic-ai-5g

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env  # optional; adjust API_PORT, LOG_LEVEL, etc. as needed

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Once running, the key endpoints are:

- `GET /health` – basic health check.
- `POST /pcf/policy/update` – apply a policy to the PCF mock.
- `GET /pcf/policy` – list all stored/applied policies.
- `GET /metrics` – Prometheus metrics exposition.

---

## Endpoint Details and Sample JSON Payloads

### 1. `GET /health`

**Description:** Liveness check for the API.

**Sample request:**

```bash
curl -X GET "http://localhost:8000/health"
```

**Sample response (200 OK):**

```json
{
  "status": "ok",
  "service": "5g-agentic-policy-optimizer"
}
```

---

### 2. `POST /pcf/policy/update`

**Description:**  
Mock PCF endpoint to **apply a single policy action**.  
Stores the policy in-memory, increments Prometheus counters, and logs the enforcement event in structured JSON.

**Request schema (`PolicyUpdateRequest`):**

- `request_id` – string identifier for this update request.
- `action` – `PolicyAction`:
  - `action_id` – unique action id.
  - `description` – human-readable description.
  - `target_slice` – one of `"eMBB"`, `"URLLC"`, `"mMTC"`, `"ENTERPRISE"`.
  - `new_allocation_percent` – float in \[0, 100].

**Sample request:**

```bash
curl -X POST "http://localhost:8000/pcf/policy/update" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-001",
    "action": {
      "action_id": "act-embb-boost",
      "description": "Increase eMBB bandwidth to handle peak traffic",
      "target_slice": "eMBB",
      "new_allocation_percent": 55.0
    }
  }'
```

**Sample response (200 OK, `PolicyUpdateResponse`):**

```json
{
  "status": "applied",
  "reason": null,
  "applied_action": {
    "action_id": "act-embb-boost",
    "description": "Increase eMBB bandwidth to handle peak traffic",
    "target_slice": "eMBB",
    "new_allocation_percent": 55.0
  }
}
```

This call also appends a `StoredPolicy` object to the in-memory store:

```json
{
  "policy_id": "req-001",
  "action": {
    "action_id": "act-embb-boost",
    "description": "Increase eMBB bandwidth to handle peak traffic",
    "target_slice": "eMBB",
    "new_allocation_percent": 55.0
  },
  "applied_at": "2026-03-04T10:20:30.123456+00:00",
  "allocations": []
}
```

---

### 3. `GET /pcf/policy`

**Description:**  
List all policies that have been applied via the PCF mock.

**Sample request:**

```bash
curl -X GET "http://localhost:8000/pcf/policy"
```

**Sample response (200 OK):**

```json
[
  {
    "policy_id": "req-001",
    "action": {
      "action_id": "act-embb-boost",
      "description": "Increase eMBB bandwidth to handle peak traffic",
      "target_slice": "eMBB",
      "new_allocation_percent": 55.0
    },
    "applied_at": "2026-03-04T10:20:30.123456+00:00",
    "allocations": []
  }
]
```

If no policies have been applied yet, this returns an empty list:

```json
[]
```

---

### 4. `GET /metrics`

**Description:**  
Prometheus metrics endpoint, exposing:

- `decision_latency_seconds` – histogram of policy decision latencies (hook-in point for the LangGraph loop).
- `sla_violations_total` – counter of SLA violations.
- `policies_applied_total` – counter of successfully applied policies (increments on `POST /pcf/policy/update`).

**Sample request:**

```bash
curl -X GET "http://localhost:8000/metrics"
```

**Sample response (snippet):**

```text
# HELP decision_latency_seconds Latency of policy decision loop
# TYPE decision_latency_seconds histogram
decision_latency_seconds_bucket{le="0.1"} 0
...
# HELP policies_applied_total Total number of policies successfully applied to PCF
# TYPE policies_applied_total counter
policies_applied_total 1.0
```

This is meant to be scraped by Prometheus; you can still inspect it via `curl` for testing.

---

## Next Steps / Extension Points

The current API is ready for testing PCF interactions and observing basic metrics.  
To evolve this into the full agentic platform described in the spec, you would:

- Implement the LangGraph StateGraph and nodes under `app/agents/`.
- Connect the telemetry simulator (`app/telemetry/simulator.py`) and ML predictor (`app/models/ml_predictor.py`) into the closed loop (`app/runtime/loop.py`).
- Add FastAPI endpoints to:
  - Accept operator intents (e.g. `"Maintain enterprise SLA at 99.9% while maximizing utilization."`),
  - Trigger or inspect agent runs and decisions.

The REST surface and schemas here are designed to be stable while those internals evolve.

