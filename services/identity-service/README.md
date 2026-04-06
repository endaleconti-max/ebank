# identity-service

Runnable MVP service for user identity and KYC workflow.

## Implemented
- POST /v1/users
- GET /v1/users/{user_id}
- GET /v1/users/{user_id}/status
- POST /v1/users/{user_id}/kyc/submit
- POST /v1/users/{user_id}/kyc/decision
- GET /v1/healthz

## Domain Rules Included
- Unique user by email.
- KYC transitions:
	- NOT_STARTED -> SUBMITTED
	- SUBMITTED -> APPROVED | REJECTED
	- REJECTED -> SUBMITTED
- Create user idempotency via Idempotency-Key bootstrap cache.

## Run
```bash
cd services/identity-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Test
```bash
cd services/identity-service
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- For Postgres, set IDENTITY_DATABASE_URL to the value in .env.example.
- Idempotency cache is in-memory for bootstrap and should be replaced with Redis or DB table.
