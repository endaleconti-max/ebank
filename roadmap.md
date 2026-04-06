# Payment App Roadmap

Date: 2026-04-05  
Version: v1.1 (Living Roadmap)

## Architecture Checkpoint (2026-04-05)
Status: Architecture created and first services implemented.

Artifacts created:
1. docs/architecture/01-system-blueprint.md
2. docs/architecture/02-service-contracts.md
3. docs/architecture/03-ledger-model.md
4. docs/architecture/04-event-catalog.md
5. contracts/apis/create-transfer.request.v1.json
6. contracts/apis/create-transfer.response.v1.json
7. contracts/events/transfer-created.v1.json
8. infra/docker-compose.dev.yml
9. services/* core service responsibility briefs
10. runnable identity-service with tests
11. runnable alias-service with tests
12. runnable ledger-service with invariant tests
13. runnable payment-orchestrator with transfer transition tests
14. runnable connector-gateway with mock adapter and callback simulation tests
15. runnable reconciliation-service with mismatch detection tests
16. cross-service contract test suite (tests/contract/) — 8 tests passing across 6 services
17. runnable api-gateway with request tracing + idempotency middleware and proxy tests
18. payment-orchestrator risk/compliance pre-check hooks with deterministic rule tests
19. payment-orchestrator connector-gateway submission hook on RESERVED→SUBMITTED_TO_RAIL
20. reconciliation-service source mode supports service clients (ledger/connector) with DB fallback
21. payment-orchestrator connector callback endpoint auto-progresses SUBMITTED_TO_RAIL -> SETTLED/FAILED
22. api-gateway forwards connector callback payloads to payment-orchestrator
23. end-to-end contract test covers orchestrator submission + connector callback + reconciliation
24. contract suite includes API gateway callback path and reconciliation service-mode variant
25. connector-gateway supports optional outbound callback forwarding to orchestrator callback endpoint
26. contract suite includes connector-driven callback forwarding end-to-end path
27. payment-orchestrator persists transfer lifecycle events and exposes transfer event history API
28. contract and service tests assert transfer lifecycle event emission on state transitions
29. payment-orchestrator exposes relay endpoint that exports only unprocessed transfer events
30. relay behavior is idempotent and verified in orchestrator + contract test suites
31. connector-gateway persists transaction status history and exposes filtered transaction-events API
32. reconciliation service-mode contract can source connector records from connector transaction-events feed
33. api-gateway exposes `POST /v1/transfers/events/relay` that forwards to orchestrator with request-id propagation
34. contract suite covers api-gateway relay path with idempotent second call guard
35. payment-orchestrator exposes `GET /v1/transfers` with `sender_user_id`, `status`, `limit`, and cursor-based pagination
36. api-gateway exposes `GET /v1/transfers` passthrough and contract suite validates pagination and filtering end-to-end
37. payment-orchestrator exposes `POST /v1/transfers/{transfer_id}/cancel` that transitions CREATED/VALIDATED/RESERVED → FAILED with reason CANCELLED
38. api-gateway exposes `POST /v1/transfers/{transfer_id}/cancel` passthrough; contract suite verifies cancellation from multiple states and that FAILED list shows cancelled transfers
39. api-gateway exposes `GET /v1/transfers/{transfer_id}/events` passthrough to orchestrator transfer lifecycle history endpoint
40. contract suite validates gateway transfer-events passthrough for both SETTLED and CANCELLED transfer flows
41. api-gateway exposes `GET /v1/connectors/transaction-events` passthrough backed by dedicated connector client and query forwarding
42. contract suite validates gateway connector transaction-events passthrough filtering by `external_ref` and `status`, including latest-by-ref state expectations
43. api-gateway exposes `GET /v1/connectors/transactions/{external_ref}` passthrough for latest connector transaction lookup
44. contract suite validates gateway connector transaction lookup reflects callback-driven status progression (`PENDING` -> `CONFIRMED`) for a single external reference
45. api-gateway exposes `GET /v1/connectors/transactions` passthrough for latest connector transaction listing
46. contract suite validates gateway connector transactions list reflects callback-updated statuses and remains consistent with latest-by-ref state derived from connector transaction-events

Immediate implementation sequence:
1. ~~Add cross-service contract test suite.~~ ✓ Done — 8 contract tests cover identity→alias, orchestrator→ledger, and connector→reconciliation flows.
2. ~~Add API gateway facade and request idempotency middleware.~~ ✓ Done — `services/api-gateway` added with middleware + tests.
3. ~~Wire risk/compliance pre-checks into transfer state machine.~~ ✓ Done — CREATED→VALIDATED now runs pre-check hooks and can auto-fail.
4. ~~Connect orchestrator to connector-gateway via internal service client.~~ ✓ Done — RESERVED→SUBMITTED_TO_RAIL now submits payout and can auto-fail.
5. ~~Replace direct DB reconciliation reads with service clients or event-driven snapshots.~~ ✓ Done — `RECON_SOURCE_MODE=service` reads from ledger/connector APIs.

Immediate next implementation sequence:
1. ~~Add end-to-end integration tests that cover orchestrator submission + connector callback + reconciliation run.~~ ✓ Done — added to `tests/contract`.
2. ~~Add API gateway forwarding endpoint for connector callbacks to orchestrator.~~ ✓ Done — `POST /v1/transfers/callbacks/connector`.

Immediate next implementation sequence:
1. ~~Add API gateway route coverage in contract tests for callback forwarding path.~~ ✓ Done — in `tests/contract/test_gateway_and_service_mode_contracts.py`.
2. ~~Add reconciliation service-mode contract variant (`RECON_SOURCE_MODE=service`) in contract suite.~~ ✓ Done — in `tests/contract/test_gateway_and_service_mode_contracts.py`.

Immediate next implementation sequence:
1. ~~Add connector-gateway outbound callback forwarding option to api-gateway/orchestrator callback endpoint.~~ ✓ Done — optional forwarding added.
2. ~~Add contract test that validates connector-gateway callback forwarding behavior end-to-end.~~ ✓ Done — added to contract suite.

Immediate next implementation sequence:
1. ~~Add a lightweight event/outbox model for transfer lifecycle events in orchestrator.~~ ✓ Done — `TransferEvent` model + `GET /v1/transfers/{transfer_id}/events` in orchestrator.
2. ~~Add contract assertions for event emission on transfer state transitions.~~ ✓ Done — assertions added in orchestrator and contract suites.

Immediate next implementation sequence:
1. ~~Add a minimal relay job in payment-orchestrator to export unprocessed transfer events for downstream consumers.~~ ✓ Done — `POST /v1/transfers/events/relay` exports and marks unrelayed events.
2. ~~Add service/contract coverage that verifies relay idempotency (same event not exported twice).~~ ✓ Done — repeat relay call returns zero exported events.

Immediate next implementation sequence:
1. ~~Add a connector-gateway events endpoint to expose callback transaction history by external reference and status.~~ ✓ Done — `GET /v1/connectors/transaction-events` with `external_ref` and `status` filters.
2. ~~Add reconciliation contract coverage that uses connector events endpoint as source data for service-mode reconciliation.~~ ✓ Done — service-mode contract now derives connector records from connector events feed.

Immediate next implementation sequence:
1. ~~Add an API-gateway endpoint for orchestrator event relay (`/v1/transfers/events/relay`) with request id propagation.~~ ✓ Done — `POST /v1/transfers/events/relay` added to api-gateway with request-id forwarding.
2. ~~Add contract coverage for API-gateway-mediated relay path including idempotent second relay call.~~ ✓ Done — `test_gateway_event_relay_contract` in `tests/contract/test_gateway_and_service_mode_contracts.py`.

Immediate next implementation sequence:
1. ~~Add `GET /v1/transfers` list endpoint to payment-orchestrator with `sender_user_id`, `status`, `limit`, and `cursor` filter params.~~ ✓ Done — `list_transfers()` in service + route; offset-based cursor via base64.
2. ~~Add api-gateway passthrough for the transfers list endpoint and add contract coverage asserting pagination and status filtering work end-to-end.~~ ✓ Done — `list_transfers()` in `OrchestratorClient`, gateway route, unit test, and `test_transfer_list_contract` in contract suite.

Immediate next implementation sequence:
1. ~~Add a transfer cancellation endpoint (`POST /v1/transfers/{transfer_id}/cancel`) to the payment-orchestrator that transitions CREATED/VALIDATED/RESERVED → FAILED with a `CANCELLED` reason.~~ ✓ Done — `cancel_transfer()` in service + route; 409 on non-cancellable states.
2. ~~Add api-gateway passthrough for the cancel endpoint and contract coverage verifying a cancelled transfer appears as FAILED in the transfers list.~~ ✓ Done — `cancel_transfer()` in `OrchestratorClient`, gateway route, unit test, and `test_cancel_transfer_contract` in contract suite.

Immediate next implementation sequence:
1. ~~Add a `GET /v1/transfers/{transfer_id}/events` passthrough to the api-gateway so callers can retrieve the full lifecycle event history for a transfer without hitting the orchestrator directly.~~ ✓ Done — added route + orchestrator client method + gateway unit test.
2. ~~Add contract coverage asserting the gateway events passthrough returns the full event sequence for a completed (SETTLED) transfer, including a CANCELLED event for a cancelled transfer.~~ ✓ Done — `test_gateway_transfer_events_passthrough_contract` added to contract suite.

Immediate next implementation sequence:
1. ~~Add API-gateway passthrough for `GET /v1/connectors/transaction-events` so external callers can query connector transaction status history without direct connector-gateway access.~~ ✓ Done — added connector client + gateway route + unit coverage.
2. ~~Add contract coverage verifying gateway connector-events passthrough filters by `external_ref` and `status` and remains consistent with reconciliation service-mode reader expectations.~~ ✓ Done — `test_gateway_connector_transaction_events_passthrough_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add API-gateway passthrough for `GET /v1/connectors/transactions/{external_ref}` to fetch latest connector transaction record by external reference.~~ ✓ Done — added connector client lookup method + gateway route + unit test.
2. ~~Add contract coverage verifying the gateway transaction passthrough reflects callback-updated status changes (for example `PENDING` -> `CONFIRMED`) for a single `external_ref`.~~ ✓ Done — `test_gateway_connector_transaction_lookup_status_progression_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add API-gateway passthrough for `GET /v1/connectors/transactions` to expose latest connector transactions list through the gateway.~~ ✓ Done — added connector client list method + gateway route + unit test.
2. ~~Add contract coverage verifying gateway transaction list passthrough returns callback-updated statuses and stays consistent with connector transaction-events-derived latest state.~~ ✓ Done — `test_gateway_connector_transactions_list_passthrough_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for connector callback simulation endpoint (`POST /v1/connectors/simulate-callback`) to support controlled test orchestration via a single gateway entry point.~~ ✓ Done — added `simulate_callback` to ConnectorClient + gateway route + unit test.
2. ~~Add contract coverage verifying gateway simulate-callback passthrough can drive status transition from `PENDING` to `CONFIRMED` and is observable via both gateway transaction lookup and transaction-events endpoints.~~ ✓ Done — `test_gateway_simulate_callback_passthrough_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for `POST /v1/transfers/callbacks/connector` so the orchestrator callback path is exercisable via the gateway in addition to direct connector-gateway webhook delivery.~~ ✓ Done — existing gateway route retained and unit coverage tightened to verify forwarded payload and request ID.
2. ~~Add contract coverage verifying gateway connector-callback passthrough drives an orchestrator transfer from `SUBMITTED_TO_RAIL` to `SETTLED` and that the resulting transfer state is observable via the gateway transfer lookup endpoint.~~ ✓ Done — `test_gateway_callback_forwarding_contract` now verifies both callback settlement and follow-up gateway transfer lookup.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for `POST /v1/reconciliation/runs` so reconciliation can be executed from the unified gateway entry point.~~ ✓ Done — added dedicated reconciliation client + gateway route + unit test.
2. ~~Add contract coverage verifying a reconciliation run triggered through the gateway completes successfully in service mode and exposes mismatch-free results for a matched ledger and connector record.~~ ✓ Done — `test_gateway_reconciliation_run_service_mode_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for `GET /v1/reconciliation/runs/{run_id}` so reconciliation results can be retrieved through the same gateway after execution.~~ ✓ Done — added reconciliation client detail method + gateway route + unit test.
2. ~~Add contract coverage verifying a run created through the gateway can be fetched again through the gateway and preserves matched/mismatch counts plus mismatch details.~~ ✓ Done — `test_gateway_reconciliation_run_detail_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for `POST /v1/transfers/{transfer_id}/transition` so orchestrator lifecycle advancement can be exercised through the unified gateway entry point.~~ ✓ Done — added `transition_transfer` to OrchestratorClient + gateway route + unit test.
2. ~~Add contract coverage verifying a transfer created through the gateway can be transitioned through `VALIDATED` and `RESERVED` via the gateway and remains observable via gateway transfer lookup and events.~~ ✓ Done — `test_gateway_transfer_transition_contract` added and passing.

Immediate next implementation sequence:
1. ~~Add api-gateway passthrough for `POST /v1/transfers/{transfer_id}/transition` to `SUBMITTED_TO_RAIL` so the full end-to-end happy path (create → validate → reserve → submit → callback → settle) can be driven entirely through the gateway.~~ ✓ Done — existing transition route already handles all status values including SUBMITTED_TO_RAIL.
2. ~~Add contract coverage verifying the full CREATED→SETTLED lifecycle driven purely through gateway endpoints, with connector-gateway simulate-callback injected mid-flow and the final SETTLED state observable via gateway transfer lookup.~~ ✓ Done — `test_gateway_full_e2e_happy_path_contract` added and passing (24 contract tests total).

Immediate next implementation sequence:
1. ~~Add idempotency enforcement to the api-gateway create-transfer route so that a second request with the same `Idempotency-Key` header returns the original response without forwarding to the orchestrator again.~~ ✓ Done — `IdempotencyMiddleware` (fingerprint-keyed in-memory cache, enforces header presence) already implemented; gateway unit tests `test_create_transfer_requires_idempotency_key` and `test_idempotency_replays_successful_create` already passing (15 gateway unit tests).
2. ~~Add contract coverage verifying that a duplicate create-transfer request (same `Idempotency-Key`) through the gateway returns the cached first response rather than creating a second transfer.~~ ✓ Done — `test_gateway_idempotency_contract` added and passing (25 contract tests total).

Immediate next implementation sequence:
1. Add a `FAILED` terminal state transition to the payment-orchestrator so that transfers that cannot be submitted or that receive a terminal failure callback can be moved to `FAILED` status with a `failure_reason` field recorded.
2. Add contract coverage verifying that a transfer transitioned to `FAILED` via the gateway returns `FAILED` status on lookup and the failure reason is present in the events feed.

## 1. Vision
Build a secure payment app where people can send and receive money using a mobile number, while enabling scalable connectivity to banks through a unified integration layer.

## 2. Strategic Objectives
1. Enable instant and reliable user-to-user payments via mobile numbers.
2. Support regulated money movement through compliant banking/payment rails.
3. Create a bank-agnostic platform that can onboard new financial institutions with minimal rework.
4. Reach launch readiness in one market, then scale to additional banks and regions.

## 3. Product Scope
### In Scope (MVP)
1. User onboarding and identity verification (KYC).
2. Mobile number verification and alias mapping.
3. Send/receive/request payment flows.
4. Transaction history and status tracking.
5. Core ledger and payment orchestration.
6. At least one funding rail and one payout rail.
7. Basic refund/dispute support.
8. Admin backoffice for support and operations.

### Out of Scope (MVP)
1. Cross-border transfers.
2. Crypto payments.
3. Full merchant acquiring stack.
4. Multi-country launch in parallel.

## 4. Non-Negotiable System Requirements
1. Double-entry accounting ledger.
2. Idempotent transaction APIs.
3. Full audit trail and immutable event logs.
4. Reconciliation at transaction and batch level.
5. Privacy-safe phone number lookup.
6. Fraud prevention and transaction risk controls.
7. Regulatory compliance by market.
8. Security baseline (encryption, key management, incident response).

## 5. High-Level Architecture
### Core Services
1. Identity Service: user profile, account status, KYC state.
2. Alias Service: phone verification, alias binding, lifecycle.
3. Ledger Service: account balances, journal entries, postings.
4. Payment Orchestrator: transfer state machine and routing.
5. Bank Connector Layer: unified interface + adapters per bank/provider.
6. Risk/Fraud Service: scoring, rules, limits, velocity checks.
7. Compliance Service: AML monitoring, sanctions screening, case workflows.
8. Reconciliation Service: internal vs external matching and exceptions.
9. Notification Service: push/SMS/email status updates.
10. Operations/Admin Service: support, refunds, disputes, manual review tooling.

### Cross-Cutting Components
1. Event bus for payment lifecycle events.
2. Observability stack (metrics, logs, traces, alerting).
3. Secure secrets and key management.
4. Analytics and reporting pipeline.

## 6. Phase Roadmap (12-18 Months)

### Phase 0: Discovery and Feasibility (Weeks 1-4)
#### Goals
- Finalize launch market and legal route.
- Freeze MVP scope.

#### Work
1. Evaluate target market options and constraints.
2. Compare licensing models (direct license vs sponsor model).
3. Define product requirements and user journeys.
4. Build unit economics baseline.

#### Deliverables
1. PRD v1 draft.
2. Legal and compliance feasibility memo.
3. MVP scope and exclusion list.
4. KPI baseline.

#### Exit Criteria
1. Launch market chosen.
2. Legal route approved.
3. MVP frozen for build.

### Phase 1: Compliance and Partner Strategy (Weeks 3-10)
#### Goals
- Design compliant operating model.
- Lock integration path for first launch rails.

#### Work
1. Select KYC/AML/sanctions vendors.
2. Define transaction monitoring scenarios and thresholds.
3. Build partner scorecard and shortlist.
4. Start partner negotiations (SLA, cost, technical terms).

#### Deliverables
1. Compliance operating model.
2. Partner due diligence matrix.
3. Contract-ready integration path.

#### Exit Criteria
1. Preferred partner selected.
2. Compliance controls approved.

### Phase 2: Core Platform Foundation (Weeks 8-18)
#### Goals
- Build the technical foundation for safe money movement.

#### Work
1. Implement identity and account core.
2. Implement alias registration and discovery APIs.
3. Build ledger primitives and posting rules.
4. Build transfer orchestration with idempotency.
5. Implement bank connector abstraction and mock adapter.

#### Deliverables
1. End-to-end sandbox transfer.
2. API contracts and versioning strategy.
3. Security threat model.

#### Exit Criteria
1. Sandbox transfer flow stable.
2. Ledger consistency tests passing.

### Phase 3: Integrations and Operational Readiness (Weeks 16-30)
#### Goals
- Integrate real rails and make operations launch-ready.

#### Work
1. Integrate first real funding and payout rails.
2. Build reconciliation jobs and exception queues.
3. Build support and compliance backoffice tools.
4. Implement fraud scoring and rule actions.

#### Deliverables
1. Pre-production with partner connectivity.
2. Reconciliation dashboard and runbooks.
3. Incident response playbooks.

#### Exit Criteria
1. Controlled real-money pilot possible under limits.
2. Operations team can resolve priority incidents.

### Phase 4: Pilot and Public Launch (Weeks 28-40)
#### Goals
- Validate performance and risk controls before broad release.

#### Work
1. Run internal alpha and limited pilot.
2. Track conversion, success rate, fraud loss, support load.
3. Tune limits and risk policies.
4. Execute launch readiness review.

#### Deliverables
1. Pilot performance report.
2. Launch checklist and approvals.
3. Launch command process.

#### Exit Criteria
1. Pilot KPIs meet thresholds.
2. Public launch approved.

### Phase 5: Scale and Multi-Bank Expansion (Weeks 40-72)
#### Goals
- Improve reliability and expand bank connectivity.

#### Work
1. Add adapters for additional banks.
2. Implement routing and failover strategy.
3. Improve fraud automation and case tooling.
4. Ship retention features.

#### Deliverables
1. Multi-bank routing policy.
2. Connector reliability scorecards.
3. Scale roadmap v2.

#### Exit Criteria
1. Bank coverage targets hit.
2. Reliability SLO targets met.

## 7. Workstream Breakdown
### A) Product and UX
1. Onboarding and verification UX.
2. Phone-based recipient discovery and confirmation.
3. Send/receive/request flows.
4. Error and recovery UX.
5. Accessibility and localization baseline.

### B) Mobile Number Alias Infrastructure
1. OTP verification and binding.
2. Alias lifecycle and ownership changes.
3. Discoverability and privacy settings.
4. Anti-enumeration and abuse throttling.
5. Number reassignment handling.

### C) Core Payments and Ledger
1. Transfer lifecycle orchestration.
2. Posting engine and account model.
3. Reversals, refunds, disputes.
4. Settlement and reconciliation.
5. Financial reporting exports.

### D) Bank Integrations
1. Connector interface standard.
2. Bank/provider adapter implementation.
3. Connector health monitoring.
4. Contract/API version handling.
5. Fallback routing policies.

### E) Risk and Compliance
1. KYC/KYB checks and risk tiers.
2. AML monitoring rules.
3. Sanctions and PEP screening.
4. Case management workflow.
5. Regulatory reporting process.

### F) Security and Reliability
1. Authentication and session security.
2. Encryption and key lifecycle management.
3. Secret management controls.
4. Incident response and security operations.
5. Service observability and SRE practices.

## 8. First 90 Days (Execution Plan)
### Day 0-30
1. Decide launch market.
2. Finalize legal and licensing approach.
3. Rank top 5 partners using scorecard.
4. Complete PRD sections for onboarding, alias, transfer, support.
5. Finalize architecture blueprint.

### Day 31-60
1. Build identity and alias skeleton services.
2. Build ledger primitives and posting logic.
3. Build transfer orchestrator happy path.
4. Add security baseline and observability.
5. Add mock connector adapter.

### Day 61-90
1. Integrate first partner sandbox.
2. Build reconciliation and exception handling MVP.
3. Build support and operations console v1.
4. Prepare pilot readiness checklist and test pack.

## 9. Milestones
1. M1: Legal route and MVP scope frozen.
2. M2: End-to-end sandbox transfer completed.
3. M3: First live rail integration completed.
4. M4: Controlled pilot readiness approved.
5. M5: Public launch completed.
6. M6: Additional bank adapter(s) integrated.

## 10. KPI Framework
### Primary KPIs
1. Onboarding completion rate.
2. Transfer success rate.
3. Fraud loss basis points.
4. Reconciliation mismatch rate.
5. Day-30 retention.

### Supporting KPIs
1. Median transfer completion time.
2. P95 transfer completion time.
3. KYC pass rate.
4. False positive fraud flag rate.
5. Support resolution time.

## 11. Risk Register (Initial)
1. Licensing delays.
2. Partner integration delays.
3. Fraud spikes after launch.
4. Wrong-recipient risk from number reuse.
5. Reconciliation mismatches.
6. Data privacy non-compliance risk.

For each risk track:
1. Owner.
2. Probability.
3. Impact.
4. Mitigation.
5. Escalation trigger.

## 12. Team and Ownership
1. Product Lead.
2. Engineering Lead/Architect.
3. Mobile Engineers.
4. Backend Payment Engineers.
5. Compliance Lead.
6. Risk/Fraud Analyst.
7. DevOps/SRE.
8. QA Automation Engineer.
9. Legal Counsel.
10. Partnerships Manager.
11. Support Operations Lead.

## 13. Partner Scorecard Template (Weighted)
Use scores from 1-5, weighted total = 100.
1. Regulatory compatibility (20).
2. API maturity and docs quality (15).
3. Required rail coverage (15).
4. Settlement and recon support (10).
5. SLA/uptime commitments (10).
6. Integration complexity and sandbox quality (10).
7. Commercial model (10).
8. Operational support quality (5).
9. Security certifications and controls (5).

Weighted score formula:
- Sum of ((score / 5) * weight) across all criteria.

## 14. Backlog Template
### Story Format
1. Story ID and title.
2. User story statement.
3. Acceptance criteria (Given/When/Then).
4. Non-functional criteria.
5. Dependencies.
6. Security/compliance impact.
7. Definition of done.

### Definition of Ready
1. Scope clear.
2. Acceptance criteria testable.
3. Dependencies known.
4. Compliance/security review complete.

### Definition of Done
1. Tests pass.
2. Monitoring added.
3. Documentation updated.
4. Runbook impact assessed.
5. Security/compliance checks complete.

## 15. Governance Cadence
1. Weekly product and engineering planning.
2. Weekly risk and compliance review.
3. Weekly partner integration status.
4. Weekly launch readiness tracking.
5. Monthly executive decisions review.

Weekly outputs:
1. Top blockers and owners.
2. Updated risk register.
3. KPI snapshot.
4. Decision log updates.
5. Next sprint plan.

## 16. Decision Log Template
1. Decision ID.
2. Date.
3. Context.
4. Decision made.
5. Alternatives considered.
6. Trade-offs.
7. Owner.
8. Follow-up actions.

Initial pending decisions:
1. D-001 Launch country.
2. D-002 Licensing route.
3. D-003 Partner model (aggregator vs direct).
4. D-004 Ledger implementation (build vs vendor).

### Recommended Decisions (Draft To Ratify)
1. D-001 Launch country selection approach: choose one country using weighted score across regulatory speed, instant-rail readiness, partner availability, fraud environment, and TAM.
2. D-002 Licensing route: launch with sponsor-bank/BaaS model first, then evaluate direct licensing after product-market and control maturity.
3. D-003 Partner model: use hybrid integration strategy.
4. D-004 Ledger strategy: build internal core ledger with strict v1 scope and external audit validation.

### Decision Rationale Snapshot
1. Sponsor model reduces time-to-launch and lowers initial regulatory overhead.
2. Hybrid partner strategy avoids single-vendor lock-in and allows staged direct-bank expansion.
3. Internal ledger ownership improves control, reconciliation quality, and long-term flexibility.

### Ratification Criteria (Required Before Lock)
1. Legal confirms licensing route suitability for chosen market.
2. Compliance confirms KYC/AML obligations are fully supported by selected vendors/partners.
3. Engineering confirms ledger implementation can meet audit, performance, and reliability requirements.
4. Finance confirms unit economics remain viable under selected partner cost model.

## 17. Continuation Protocol
When resuming this roadmap:
1. Update date and version.
2. Mark milestones completed/in-progress.
3. Record top 5 blockers.
4. Update decision log.
5. Produce next 2-week sprint plan with owners and dependencies.

Resume command:
- "Continue roadmap from current checkpoint and generate next sprint."

## 18. Assumptions and Constraints
### Assumptions
1. Launch starts in one market before multi-country expansion.
2. Initial launch uses at least one sponsor bank or BaaS partner.
3. Mobile phone number is the primary user identifier for payment discovery.
4. Real-time transfer is prioritized where rails allow it; fallback rails may be near-real-time.
5. Team starts lean and scales by milestone.

### Constraints
1. Regulatory approval timelines may be outside product control.
2. Partner integration quality may vary significantly.
3. Fraud risk will increase with growth and promotional campaigns.
4. Number recycling by telcos introduces recipient-risk edge cases.

## 19. Compliance Artifact Checklist
Required artifacts before public launch:
1. KYC/KYB policy and operating procedure.
2. AML and sanctions policy with escalation matrix.
3. Customer risk-tiering methodology and transaction limits policy.
4. Data privacy notice, consent record model, and retention policy.
5. Incident response and breach notification procedure.
6. Internal audit evidence map (control -> evidence source -> owner).
7. Regulatory reporting calendar and accountable owner.

Launch compliance gates:
1. All mandatory controls mapped to product flows.
2. Case management workflow tested end-to-end.
3. Sampling evidence produced for onboarding, screening, and transaction monitoring.

## 20. API and Data Contract Baseline
### Minimum API surfaces for MVP
1. Identity API: register user, update profile, fetch account state.
2. Alias API: verify number, bind alias, unbind alias, lookup recipient.
3. Transfer API: initiate transfer, get status, cancel (where legal/possible), retry-safe submit.
4. Ledger API (internal): create posting batch, query balances, query journal entries.
5. Reconciliation API (internal): ingest partner statements, run matching job, list exceptions.

### Data contract requirements
1. Every transfer must have globally unique transfer_id and idempotency_key.
2. Every ledger posting must reference source_event_id.
3. Every externally visible state transition must be evented.
4. PII fields must be classified and tagged for storage, access, and retention control.

### Canonical transfer states
1. created
2. pending_risk
3. pending_partner
4. posted
5. settled
6. failed
7. reversed

## 21. NFR Targets and SLOs
Initial targets (to refine per market and partner capability):
1. API availability: 99.9% monthly for core transfer endpoints.
2. Transfer API latency: p95 < 800ms for non-partner synchronous operations.
3. Event processing delay: p95 < 5 seconds.
4. Reconciliation completion: daily batch complete by T+1 06:00 local time.
5. Data durability: no acknowledged transfer event loss.

Error budget policy:
1. If monthly availability falls below SLO, freeze non-critical feature releases until stability recovers.

## 22. Security Control Matrix (Minimum)
1. Authentication: MFA for high-risk actions and device binding for returning sessions.
2. Authorization: least privilege RBAC for admin and support tools.
3. Encryption: TLS in transit and encrypted storage for sensitive data.
4. Key lifecycle: rotation schedule, dual-control for production key operations.
5. Secrets: centralized secrets manager, no plaintext secrets in code or logs.
6. Detection: anomalous login, payout velocity, and account takeover alerts.
7. Recovery: tested incident runbook for fraud, outage, and data incidents.

## 23. Testing and Quality Gates
### Test layers
1. Unit tests for domain logic (ledger posting rules, risk rules).
2. Integration tests for service-to-service contracts.
3. Contract tests for each bank connector.
4. End-to-end tests for onboarding and transfer journeys.
5. Resilience tests for partner timeout and retry behavior.

### Mandatory pre-launch quality gates
1. Critical payment paths covered by automated tests.
2. No open critical or high-severity security issues.
3. Reconciliation mismatch rate below launch threshold.
4. Runbook drill completed with incident commander and responders.

## 24. Launch and Rollback Plan
### Launch stages
1. Internal employee alpha.
2. Invite-only pilot with strict limits.
3. Gradual public rollout by cohorts.

### Guardrails
1. Real-time monitoring on success rate, fraud rate, and partner error rate.
2. Dynamic transaction limits by trust tier.
3. Kill-switch for partner routing path and risky feature flags.

### Rollback triggers
1. Transfer success rate below minimum threshold for defined window.
2. Fraud loss spike beyond risk tolerance.
3. Reconciliation mismatch above escalation threshold.

### Rollback actions
1. Disable affected rails/features via flags.
2. Route to fallback partner when available.
3. Move to receive-only mode if sending integrity is at risk.

## 25. Financial Operations and Treasury Controls
1. Daily cash position report by rail and partner.
2. Safeguarding/segregation account controls and sign-off workflow.
3. Funding buffer policy for payout continuity.
4. Fee calculation and revenue recognition checks.
5. Monthly finance-control review with reconciliation aging analysis.

## 26. Delivery Plan: Next 2 Sprints (Actionable)
### Sprint A (2 weeks)
1. Finalize launch-country decision package (owner: Product + Legal).
2. Close D-002 licensing route recommendation (owner: Legal/Compliance).
3. Complete partner weighted scorecard and shortlist top 3 (owner: Partnerships).
4. Finish PRD sections for onboarding, alias, transfer, support (owner: Product).
5. Define KPI dictionary and dashboard specs (owner: Product Analytics).

### Sprint B (2 weeks)
1. Implement identity service skeleton endpoints (owner: Backend).
2. Implement alias verification and bind/unbind endpoints (owner: Backend).
3. Implement ledger journal and posting primitives (owner: Backend).
4. Implement transfer initiation with idempotency enforcement (owner: Backend).
5. Add baseline observability and error taxonomy (owner: SRE/Backend).

## 27. Critical Path Dependencies
1. Launch-country decision -> licensing route -> partner contract -> live integration.
2. Identity and KYC completion -> alias activation -> transfer enablement.
3. Ledger and transfer engine readiness -> reconciliation readiness -> pilot go-live.
4. Compliance controls testing -> launch approval.

Primary blockers to track weekly:
1. Legal and licensing turnaround time.
2. Partner API readiness and sandbox stability.
3. Fraud rule tuning quality before pilot scale-up.
4. Reconciliation mismatch closure cycle time.

## 28. Open Questions (To Resolve)
1. Which launch market gives best balance of speed, TAM, and compliance complexity?
2. Which partner model is best for first launch: aggregator, direct bank, or hybrid?
3. What initial transfer limits should be set by user risk tier?
4. What recipient-confirmation UX minimizes wrong-recipient errors while preserving speed?
5. What is the minimum team composition required for 24/7 incident readiness at launch?

## 29. Proposed Answers To Open Questions (Working Draft)
1. Launch market: use the weighted country scorecard and select one market where regulatory route and bank connectivity can be delivered fastest with acceptable fraud exposure.
2. Partner model: hybrid is recommended for launch.
3. Initial transfer limits by risk tier:
	- Tier 0 (new/unverified profile): low daily and monthly caps; receive-only optional.
	- Tier 1 (KYC complete, low risk): moderate caps.
	- Tier 2 (history established, low fraud score): higher caps.
	- Tier 3 (enhanced due diligence or premium users): highest caps with ongoing monitoring.
4. Recipient confirmation UX:
	- Show recipient legal/preferred name and masked number before final confirmation.
	- Require explicit confirmation on first transfer to a new alias.
	- Add short cooling warning for high-value first-time recipients.
5. Minimum 24/7 launch readiness composition:
	- One incident commander/on-call lead.
	- One backend payment engineer.
	- One SRE/platform engineer.
	- One fraud/risk analyst on escalation.
	- One support operations lead.

## 30. Immediate 14-Day Execution Checklist
1. Finalize weighted launch-country scorecard fields and weights.
2. Run country comparison for top 3 candidates and recommend one.
3. Validate D-002 and D-003 with legal, compliance, and partnerships.
4. Produce v1 transfer-limit table for risk tiers with compliance sign-off.
5. Write recipient-confirmation UX acceptance criteria in PRD.
6. Define 24/7 on-call schedule and escalation matrix for pilot.
7. Move ratified decisions into a dated decision log entry block.

Definition of success after 14 days:
1. D-001 through D-004 are ratified or blocked with named owner and due date.
2. Pilot control settings (limits, confirmations, escalation) are documented and approved.
3. Sprint backlog is unblocked for implementation workstream start.
