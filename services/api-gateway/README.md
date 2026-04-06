# api-gateway

Runnable MVP API facade for external entrypoints, request tracing, and idempotency enforcement.

## Implemented
- POST /v1/transfers (forwards to payment-orchestrator)
- GET /v1/transfers/{transfer_id} (forwards to payment-orchestrator)
- POST /v1/transfers/callbacks/connector (forwards connector callback to payment-orchestrator)
- GET /v1/healthz

## Middleware Included
- Request context middleware:
  - Accepts incoming X-Request-Id or generates one.
  - Echoes X-Request-Id on responses.
- Idempotency middleware (bootstrap):
  - Enforced on mutating transfer creation.
  - Requires Idempotency-Key.
  - Replays cached successful responses for identical method+path+key+body.

## Run
```bash
cd services/api-gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Test
```bash
cd services/api-gateway
source .venv/bin/activate
pytest -q
```

## Notes
- This MVP proxies to payment-orchestrator using ORCHESTRATOR_BASE_URL.
- The idempotency cache is in-memory and should be replaced with Redis/DB for production.
