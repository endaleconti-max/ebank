# eBank Audit 02: Gap-to-Roadmap Matrix

Date: 2026-04-06
Reference roadmap: ../../roadmap.md

## Legend
- Done: Implemented with direct evidence
- In Progress: Partial implementation, not launch-complete
- Gap: Not implemented in repository

## Phase 0 to 1 (Discovery, Compliance Strategy)

| Roadmap Need | State | Gap Detail | Priority |
|---|---|---|---|
| Legal and licensing route artifacts | Gap | No legal/compliance decision artifacts in repo | High |
| Vendor strategy for KYC/AML/sanctions | In Progress | KYC states exist in identity service, but vendor integrations absent | High |
| Compliance operating model | Gap | No policy or case workflow implementation found | High |

## Phase 2 (Core Platform Foundation)

| Roadmap Need | State | Evidence | Gap Detail |
|---|---|---|---|
| Identity and account core | Done | ../../services/identity-service/app/api/routes.py | Needs production auth and stronger controls |
| Alias registration and discovery | Done | ../../services/alias-service/app/api/routes.py | Needs anti-enumeration/privacy hardening |
| Ledger primitives and posting rules | Done | ../../services/ledger-service/app/domain/service.py | Needs scale and operational hardening |
| Transfer orchestration with idempotency | Done | ../../services/payment-orchestrator/app/domain/service.py | Needs full external integration lifecycle |
| Connector abstraction with mock adapter | Done | ../../services/connector-gateway/app/api/routes.py | Real rails missing |
| API contracts and architecture docs | Done | ../../contracts, ../../docs/architecture | Keep in sync with evolving APIs |

## Phase 3 (Integrations and Operational Readiness)

| Roadmap Need | State | Gap Detail | Priority |
|---|---|---|---|
| First live funding and payout rails | Gap | Connector is mock-driven; no live partner adapter | Critical |
| Reconciliation exception operations | In Progress | Reconciliation detection exists, manual workflow tooling missing | High |
| Support/admin backoffice | Gap | No ops service implementation | High |
| Fraud decision engine | In Progress | Deterministic prechecks in orchestrator only | High |
| Compliance reporting outputs | Gap | No reporting pipeline or service | High |
| Incident runbooks and operational playbooks | Gap | Not present in repository docs | Medium |

## Phase 4 (Pilot and Public Launch)

| Roadmap Need | State | Gap Detail |
|---|---|---|
| Controlled pilot instrumentation | Gap | No pilot telemetry/dashboard implementation in repo |
| KPI tracking for launch gate | Gap | No KPI module or dashboard assets found |
| Launch readiness process | Gap | No checklist artifacts or run command process docs found |

## Phase 5 (Scale and Multi-Bank Expansion)

| Roadmap Need | State | Gap Detail |
|---|---|---|
| Multi-bank adapters | Gap | Two mock connector ids only |
| Smart routing and failover | Gap | No routing policy engine found |
| Reliability scorecards | Gap | No scorecard pipeline in repo |
| Retention feature layer | Gap | No end-user app feature layer in workspace |

## Cross-Cutting Gaps

| Domain | State | Gap Detail | Priority |
|---|---|---|---|
| Authentication and authorization | Gap | Gateway has no visible OAuth/OIDC enforcement | Critical |
| Secrets and key management | Gap | No secure secret abstraction in service code | Critical |
| Event bus and outbox durability | In Progress | Outbox-like relay exists in orchestrator; no real bus integration | High |
| Observability (logs/metrics/traces) | Gap | Minimal health endpoints only | High |
| Production deployment manifests | Gap | Local docker compose exists; no production manifests | Medium |
| Client applications | Gap | Mobile/web product surfaces not present | Critical |

## Contract and Test Coverage Gaps

| Area | State | Gap Detail |
|---|---|---|
| Contract depth | In Progress | Strong backend contracts; no auth/security contracts |
| End-to-end with real connectors | Gap | Current E2E remains in-process/mocked |
| Current CI pass confirmation | In Progress | Latest terminal run exited non-zero; needs fresh triage |

## Top 10 Critical Remaining Work Items
1. Implement real connector adapter for one live payout rail.
2. Add gateway authentication and authorization enforcement.
3. Build standalone risk-service with decision API and rule/version management.
4. Build standalone compliance-service for sanctions/AML checks and case outcomes.
5. Build ops-service/admin workflows for disputes, manual review, and exception resolution.
6. Implement notification-service for customer and operational event delivery.
7. Add observability stack integration (structured logs, metrics, traces, alerts).
8. Establish production-grade idempotency and distributed locking backing store.
9. Add launch KPI instrumentation and pilot reporting.
10. Add client application layer (mobile or web) for real user journeys.

## Updated Completion Read
- Core backend foundation: strong but not launch-complete.
- Full roadmap completion: still below halfway due to missing regulated operations and product surface layers.
