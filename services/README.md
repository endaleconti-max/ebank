# Services Workspace Layout

This folder contains implementation workspaces for domain services.

## Planned Services
- api-gateway
- identity-service
- alias-service
- ledger-service
- payment-orchestrator
- connector-gateway
- risk-service
- compliance-service
- reconciliation-service
- notification-service
- ops-service

## Build Sequence (First Cut)
1. api-gateway
2. identity-service
3. alias-service
4. ledger-service
5. payment-orchestrator
6. connector-gateway (mock)
7. reconciliation-service
8. cross-service contract test suite (`../tests/contract`) ✅
9. API gateway facade + idempotency middleware ✅

## Immediate Next
1. Add orchestrator transfer event/outbox model for lifecycle transitions.
2. Extend contract tests to assert expected events are recorded.

## Shared Rules
- APIs are versioned under /v1.
- Money values use integer minor units only.
- All mutating APIs require idempotency where applicable.
- Transfer lifecycle ownership stays in payment-orchestrator.

## Initial Folder Convention (per service)
- src/api
- src/domain
- src/application
- src/infrastructure
- src/events
- tests
