# reconciliation-service

Runnable MVP worker/API for transaction-level reconciliation between ledger and connector records.

## Implemented
- POST /v1/reconciliation/runs
- GET /v1/reconciliation/runs/{run_id}
- GET /v1/healthz

## Reconciliation Rules Included
- Ledger entry without connector transaction -> MISSING_CONNECTOR_TRANSACTION
- Connector transaction without ledger entry -> ORPHAN_CONNECTOR_TRANSACTION
- Amount mismatch -> AMOUNT_MISMATCH
- Currency mismatch -> CURRENCY_MISMATCH
- Connector transaction in FAILED status -> CONNECTOR_FAILED

## Data Sources
- Reads ledger data from ledger-service SQLite/Postgres export path
- Reads connector transaction data from connector-gateway SQLite/Postgres export path
- Stores reconciliation runs and mismatches locally

## Source Modes
- `RECON_SOURCE_MODE=db` (default): direct DB reads via `RECON_LEDGER_DB_PATH` and `RECON_CONNECTOR_DB_PATH`.
- `RECON_SOURCE_MODE=service`: HTTP reads from:
	- `GET /v1/ledger/entries` on ledger-service
	- `GET /v1/connectors/transactions` on connector-gateway

## Run
```bash
cd services/reconciliation-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8006
```

## Test
```bash
cd services/reconciliation-service
source .venv/bin/activate
pytest -q
```

## Notes
- Persistence defaults to SQLite for immediate local run.
- Source DB paths are configured via RECON_LEDGER_DB_PATH and RECON_CONNECTOR_DB_PATH.
- Service-client URLs are configured via RECON_LEDGER_SERVICE_BASE_URL and RECON_CONNECTOR_SERVICE_BASE_URL.
