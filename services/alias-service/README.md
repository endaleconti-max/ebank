# alias-service

Runnable MVP service for phone verification, alias binding, unbinding, and resolution.

## Implemented
- POST /v1/aliases/verify-phone
- POST /v1/aliases/bind
- POST /v1/aliases/{alias_id}/unbind
- GET /v1/aliases/resolve?phone_e164={e164}
- GET /v1/healthz

## Domain Rules Included
- Phone verification bootstrap:
	- First verify request creates verification with verified=false.
	- Second verify with same OTP marks phone verified=true.
- Alias bind requires verified phone.
- Only BOUND aliases are returned by resolve.
- Unbind transitions alias status to UNBOUND.

## Run
```bash
cd services/alias-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

## Test
```bash
cd services/alias-service
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- For Postgres, set ALIAS_DATABASE_URL to the value in .env.example.
