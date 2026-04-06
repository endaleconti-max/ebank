# payment-orchestrator

Runnable MVP service for transfer creation and state-machine transitions.

## Implemented
- POST /v1/transfers
- GET /v1/transfers/{transfer_id}
- POST /v1/transfers/{transfer_id}/transition
- POST /v1/transfers/callbacks/connector
- GET /v1/healthz

## Domain Rules Included
- `Idempotency-Key` header is required on transfer creation.
- Duplicate idempotency key returns the originally created transfer.
- CREATED -> VALIDATED transition executes risk/compliance pre-check hooks.
- A failed pre-check auto-transitions transfer to FAILED with failure_reason.
- RESERVED -> SUBMITTED_TO_RAIL submits payout to connector-gateway.
- Connector rejection or outage auto-transitions transfer to FAILED.
- Connector callback `CONFIRMED` transitions transfer to `SETTLED`.
- Connector callback `FAILED` transitions transfer to `FAILED`.
- Allowed transitions are strictly enforced:
	- CREATED -> VALIDATED | FAILED
	- VALIDATED -> RESERVED | FAILED
	- RESERVED -> SUBMITTED_TO_RAIL | FAILED
	- SUBMITTED_TO_RAIL -> SETTLED | FAILED | REVERSED
	- SETTLED -> REVERSED

## Run
```bash
cd services/payment-orchestrator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8004
```

## Test
```bash
cd services/payment-orchestrator
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- For Postgres, set ORCHESTRATOR_DATABASE_URL to the value in .env.example.
- Connector submission is configurable via ORCHESTRATOR_CONNECTOR_* settings.
