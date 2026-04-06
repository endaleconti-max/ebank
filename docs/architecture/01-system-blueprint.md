# eBank Architecture Blueprint v0.1

Date: 2026-04-05
Status: Draft for implementation start
Scope: MVP architecture for a single-country launch

## 1. Architecture Goals
- Safe money movement with strict ledger correctness.
- High delivery speed through clear service boundaries.
- Bank-agnostic connector model to add rails quickly.
- Compliance and fraud controls embedded in payment lifecycle.

## 2. Architecture Style
- Domain-oriented modular microservices.
- API-first internal contracts.
- Event-driven integration for asynchronous workflows.
- Synchronous calls only on critical user flows.

## 3. Bounded Contexts
1. Identity: user account, KYC state, auth profile.
2. Alias: phone number verification and alias lifecycle.
3. Payments: transfer orchestration and state machine.
4. Ledger: double-entry postings and balances.
5. Connectors: partner/bank adapter interface.
6. Risk: fraud decisions, velocity/limits.
7. Compliance: AML/sanctions checks and case outcomes.
8. Reconciliation: internal-external matching and exceptions.
9. Notifications: user and ops messaging.
10. Operations: admin tooling and manual interventions.

## 4. Primary Runtime Components
- API Gateway: external API edge, auth enforcement, idempotency header validation.
- Identity Service: onboarding profile, KYC status and account state.
- Alias Service: phone OTP binding, alias discovery policy checks.
- Payment Orchestrator: transfer commands, state transitions, retries.
- Ledger Service: account model, journal entries, posting invariants.
- Connector Gateway: provider-agnostic interface and adapter execution.
- Risk Service: real-time decision API and asynchronous model updates.
- Compliance Service: sanctions and monitoring signals.
- Reconciliation Service: periodic and near-real-time matching.
- Notification Service: push/SMS/email event consumers.
- Ops Service: support workflows, disputes and approvals.

## 5. Core Data Stores
- PostgreSQL per service for operational state.
- Ledger DB (PostgreSQL) with strict transaction isolation and append-only journal table.
- Redis for idempotency key cache and short-lived workflow locks.
- Object storage for reports, reconciliation exports and audit artifacts.

## 6. Messaging and Events
- Kafka-compatible bus for immutable payment lifecycle events.
- Outbox pattern in stateful services to guarantee publish-after-commit.
- Event schema versioning using semantic version field in payload.

## 7. Sync vs Async Rules
- Sync APIs: user-initiated reads/writes requiring immediate response.
- Async events: downstream side effects (notifications, analytics, secondary checks).
- No distributed transactions across services; use sagas with compensations.

## 8. Payment Lifecycle (MVP)
1. Client calls CreateTransfer with idempotency key.
2. Orchestrator validates sender, recipient alias, limits.
3. Risk and Compliance pre-checks run.
4. Ledger reserves/debits sender and credits pending settlement account.
5. Connector executes payout/funding rail action.
6. Callback/webhook updates transfer state.
7. Ledger finalizes postings and release rules.
8. Events emitted for notification and reconciliation.

## 9. Reliability and SLO Targets (Initial)
- Transfer API availability: 99.9% monthly.
- End-to-end successful transfer in rail-available scenarios: >= 98.5%.
- P95 orchestration latency excluding external rail latency: <= 400 ms.
- Reconciliation mismatch rate: <= 0.10% before manual operations close.

## 10. Security Baseline
- OAuth2/OIDC for user auth; mTLS for service-to-service calls.
- Envelope encryption for sensitive data at rest.
- Phone numbers tokenized/hash-indexed for lookup privacy controls.
- Immutable audit events for all money movement mutations.
- Least privilege IAM and scoped secrets per service.

## 11. Deployment Topology (MVP)
- Kubernetes for services and jobs.
- Managed PostgreSQL and Redis.
- Managed Kafka-compatible message bus.
- CI/CD with policy checks, migration checks, and canary rollout.

## 12. First Build Cut (Now)
- Implement services with thin vertical slices:
  - identity-service
  - alias-service
  - ledger-service
  - payment-orchestrator
  - connector-gateway (mock adapter first)
- Stub risk/compliance with deterministic rule engine.
- Add reconciliation batch worker with transaction-level matching.

## 13. Architecture Decisions To Ratify This Week
- ADR-001: monorepo vs multi-repo (recommended: monorepo).
- ADR-002: event bus platform selection.
- ADR-003: internal API style (REST for MVP, gRPC candidate for v2).
- ADR-004: ledger balance strategy (computed + snapshot cache).
