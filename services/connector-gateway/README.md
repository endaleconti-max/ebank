# connector-gateway

Runnable MVP service for connector abstraction, mock rail execution, and webhook normalization.

## Implemented
- POST /v1/connectors/{connector_id}/payouts
- POST /v1/connectors/{connector_id}/fundings
- POST /v1/connectors/{connector_id}/webhooks
- POST /v1/connectors/simulate-callback
- GET /v1/connectors/transactions/{external_ref}
- GET /v1/healthz

## Domain Rules Included
- Supported connectors: `mock-bank-a`, `mock-bank-b`.
- Unknown connector returns 404.
- `external_ref` uniqueness enforced across operations.
- Mock provider rules:
	- external ref ending with `-fail` returns immediate FAILED.
	- other refs return PENDING until callback/webhook updates status.
- Optional callback forwarding: webhook/simulated callback can be forwarded to orchestrator via configured URL.

## Run
```bash
cd services/connector-gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8005
```

## Test
```bash
cd services/connector-gateway
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- For Postgres, set CONNECTOR_DATABASE_URL to the value in .env.example.
- Callback forwarding is controlled by CONNECTOR_CALLBACK_FORWARD_ENABLED and CONNECTOR_CALLBACK_FORWARD_URL.
