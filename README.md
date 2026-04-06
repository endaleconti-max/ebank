# eBank

Initial architecture baseline generated from roadmap.md.

## What Exists Now
- Architecture blueprint and service boundaries.
- API and event contract skeletons.
- Ledger model draft with posting invariants.
- Local infrastructure compose for Postgres, Redis, and event bus.
- Runnable `identity-service` with tests.
- Runnable `alias-service` with tests.
- Runnable `ledger-service` with invariant tests.
- Runnable `payment-orchestrator` with transition tests.
- Runnable `api-gateway` facade with request tracing and idempotency middleware tests.
- Runnable `connector-gateway` with mock adapter and callback simulation tests.
- Runnable `reconciliation-service` with mismatch detection tests.
- Runnable `client-app` customer web layer for transfer flows.
- Cross-service contract suite in `tests/contract` with 12 passing tests.

## Current Structure
- docs/architecture
- contracts/apis
- contracts/events
- infra/docker-compose.dev.yml
- services

## Start Local Infra
```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

## Next Build Steps
1. Add a lightweight event/outbox model for transfer lifecycle events in orchestrator.
2. Add contract assertions for event emission on transfer state transitions.

## Contract Test Suite
Run from project root using the Python 3.9 service environment:

```bash
services/identity-service/.venv/bin/pytest tests/contract/ -v
```

## Customer Client App
```bash
cd services/client-app
python3 -m http.server 5173
```

Then open `http://localhost:5173` (the app points to `http://localhost:8000` by default).
