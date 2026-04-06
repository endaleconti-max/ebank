# eBank Audit 01: Strict Service Scorecard

Date: 2026-04-06
Audit mode: strict pass/fail by launch-critical criteria

## Scoring Method
- PASS: Implemented and covered by meaningful tests
- PARTIAL: Implemented but missing key launch controls or integration depth
- FAIL: Not implemented or only roadmap-level intent

## Service Scorecard

| Domain | Target Component | Current State | Evidence | Score | Notes |
|---|---|---|---|---|---|
| API Edge | API Gateway | Broad passthrough coverage for transfers, connectors, reconciliation | ../../services/api-gateway/app/api/routes.py, ../../services/api-gateway/tests/test_gateway_api.py | PARTIAL | Good routing and request id handling; authn/authz not present |
| Identity | identity-service | User creation and KYC transitions implemented | ../../services/identity-service/app/api/routes.py, ../../services/identity-service/tests/test_identity_api.py | PARTIAL | Lifecycle exists; no external KYC vendor integration |
| Alias | alias-service | Verify, bind, unbind, resolve implemented | ../../services/alias-service/app/api/routes.py, ../../services/alias-service/tests/test_alias_api.py | PARTIAL | Functional MVP; privacy and anti-enumeration controls not hardened |
| Ledger | ledger-service | Double-entry postings and reversals with invariants | ../../services/ledger-service/app/domain/service.py, ../../services/ledger-service/tests/test_ledger_api.py | PASS | Core accounting invariants are explicit and tested |
| Orchestration | payment-orchestrator | Full transfer state machine, callback handling, events, relay | ../../services/payment-orchestrator/app/domain/service.py, ../../services/payment-orchestrator/tests/test_orchestrator_api.py | PASS | Strong domain flow; still mock-oriented for rail integration |
| Connectors | connector-gateway | Mock bank payout/funding, callback simulation, transaction events | ../../services/connector-gateway/app/api/routes.py, ../../services/connector-gateway/tests/test_connector_gateway_api.py | PARTIAL | Mock-first only; no real provider adapter |
| Reconciliation | reconciliation-service | Run and detail APIs with mismatch classification | ../../services/reconciliation-service/app/domain/service.py, ../../services/reconciliation-service/tests/test_reconciliation_api.py | PARTIAL | Useful baseline; operations workflow and remediation loop missing |
| Cross-Service | Contract testing | Multi-service contract flows implemented | ../../tests/contract/test_gateway_and_service_mode_contracts.py, ../../tests/contract/test_end_to_end_callback_reconciliation.py | PASS | Good breadth; latest run status must be re-verified |
| Risk/Fraud | risk-service | Planned only | ../../services/README.md | FAIL | Logic currently embedded as simple orchestrator prechecks |
| Compliance | compliance-service | Planned only | ../../services/README.md | FAIL | No standalone AML/sanctions/case workflow service |
| Notifications | notification-service | Planned only | ../../services/README.md | FAIL | No message delivery service |
| Operations | ops-service | Planned only | ../../services/README.md | FAIL | No support/admin operational tool service |

## Functional Completeness Snapshot
- Core backend flow: PARTIAL-to-STRONG
- Launch controls and regulated operations: WEAK
- Full app scope (including client apps and ops maturity): INCOMPLETE

## Numeric Summary
- PASS: 4
- PARTIAL: 5
- FAIL: 4
- Strict completion index: 50.0 percent (PASS=1, PARTIAL=0.5, FAIL=0 across 13 domains)

## Immediate Implications
- Backend MVP foundation is credible.
- Launch readiness is blocked by missing dedicated risk/compliance/ops/notification services and production controls.
