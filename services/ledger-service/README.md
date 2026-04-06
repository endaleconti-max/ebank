# ledger-service

Runnable MVP service for double-entry ledger posting and reversals.

## Implemented
- POST /v1/ledger/accounts
- POST /v1/ledger/postings
- POST /v1/ledger/reversals/{entry_id}
- GET /v1/ledger/accounts/{account_id}/balance
- GET /v1/ledger/entries/{entry_id}
- GET /v1/healthz

## Domain Rules Included
- Entry must contain at least two postings.
- Sum(debits) must equal sum(credits).
- All postings in one entry must share a single currency.
- Posting currency must match account currency.
- External reference is unique and idempotency-safe for entry creation.

## Run
```bash
cd services/ledger-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

## Test
```bash
cd services/ledger-service
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- For Postgres, set LEDGER_DATABASE_URL to the value in .env.example.
