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
1. ~~Add a `FAILED` terminal state transition to the payment-orchestrator so that transfers that cannot be submitted or that receive a terminal failure callback can be moved to `FAILED` status with a `failure_reason` field recorded.~~ ✓ Done — `FAILED` status, `failure_reason` field, `ALLOWED_TRANSITIONS`, schema, and service logic were already fully implemented; orchestrator unit tests cover auto-fail from prechecks, connector submission failure, callback failure, and explicit cancel-to-FAILED (14 orchestrator tests passing).
2. ~~Add contract coverage verifying that a transfer transitioned to `FAILED` via the gateway returns `FAILED` status on lookup and the failure reason is present in the events feed.~~ ✓ Done — `test_gateway_failed_transition_contract` added: creates, advances to RESERVED, transitions to FAILED with `connector_unavailable` reason, asserts gateway lookup and events feed both expose the failure, and asserts further transitions return 409 (26 contract tests total).

Immediate next implementation sequence:
1. ~~Add a `REVERSED` terminal state path to the payment-orchestrator so that settled transfers can be reversed via an explicit transition, recording a `reversal_reason` in the events feed and marking the transfer as `REVERSED`.~~ ✓ Done — added `failure_reason` requirement for `REVERSED` transitions (same enforcement as `FAILED`), persists reason on transfer and in event; added `test_reversed_transition_from_settled_records_reason`, `test_reversed_transition_requires_reason`, `test_reversed_is_terminal` (17 orchestrator tests passing).
2. ~~Add contract coverage verifying that a SETTLED transfer transitioned to `REVERSED` via the gateway exposes the `REVERSED` status on lookup and a reversal event in the events feed.~~ ✓ Done — `test_gateway_reversed_transition_contract` added: drives full SETTLED lifecycle through gateway, reverses with `chargeback_accepted` reason, asserts lookup + events feed + terminal (27 contract tests total).

Immediate next implementation sequence:
1. ~~Add a ledger double-entry posting step to the payment-orchestrator's RESERVED→SUBMITTED_TO_RAIL transition so that funds are debited from the sender's wallet account and credited to the transit/escrow account at time of submission.~~ ✓ Done — wired via `post_transfer_entry` in `services/payment-orchestrator/app/domain/service.py`, gated by `ledger_posting_enabled`, with new optional `sender_ledger_account_id` / `transit_ledger_account_id` fields.
2. ~~Add contract coverage verifying that after a transfer reaches SUBMITTED_TO_RAIL via the gateway, the sender's ledger balance reflects the debit and the transit account reflects the credit.~~ ✓ Done — `test_gateway_ledger_posting_on_submission_contract` added in `tests/contract/test_gateway_and_service_mode_contracts.py`; test suites green: 19 orchestrator + 15 gateway + 28 contract tests.

Immediate next implementation sequence:
1. ~~Add a ledger double-entry reversal posting to the payment-orchestrator's SETTLED→REVERSED transition so that the transit account is debited and the sender's wallet account is credited back at time of reversal.~~ ✓ Done — `post_reversal_entry` is wired in `services/payment-orchestrator/app/domain/service.py` behind `ledger_posting_enabled`; orchestrator unit coverage includes enabled/disabled paths.
2. ~~Add contract coverage verifying that after a SETTLED transfer is reversed via the gateway, the transit account balance reflects the debit-back and the sender's ledger balance reflects the credit-back.~~ ✓ Done — `test_gateway_ledger_reversal_posting_on_reversed_contract` added in `tests/contract/test_gateway_and_service_mode_contracts.py`; current suites green: 21 orchestrator + 15 gateway + 29 contract tests.

Immediate next implementation sequence:
1. ~~Add strict ledger posting error handling so `RESERVED -> SUBMITTED_TO_RAIL` and `SETTLED -> REVERSED` fail atomically (or move to a compensating FAILED state) when ledger posting returns `ok=false`.~~ ✓ Done — orchestrator now moves transfers to compensating `FAILED` with ledger-provided reason when `post_transfer_entry` or `post_reversal_entry` returns `ok != true`.
2. ~~Add unit and contract coverage proving ledger failures do not silently progress transfer state and that failure reasons are exposed consistently via gateway lookup/events.~~ ✓ Done — added orchestrator unit tests for submission/reversal ledger failures and gateway contract tests asserting `FAILED` status + `failure_reason` in lookup/events; suites green: 23 orchestrator + 15 gateway + 31 contract tests.

Immediate next implementation sequence:
1. ~~Add explicit ledger failure event taxonomy and API filtering support (for example `TRANSFER_LEDGER_POSTING_FAILED` and `TRANSFER_LEDGER_REVERSAL_POSTING_FAILED`) in transfer-events queries to improve ops triage.~~ ✓ Done — payment-orchestrator and api-gateway transfer-events endpoints now accept `event_type` filtering and can isolate ledger failure events directly.
2. ~~Add contract coverage proving gateway transfer-events retrieval can filter/identify ledger-failure events for failed transfers without scanning full lifecycle histories.~~ ✓ Done — gateway contract tests now assert filtered event retrieval for both submission and reversal ledger-failure cases; suites green: 24 orchestrator + 15 gateway + 31 contract tests.

Immediate next implementation sequence:
1. ~~Add transfer-event filtering by terminal transition status (`to_status`) so operations can query only failed or reversed lifecycle events without coupling to event-type names.~~ ✓ Done — orchestrator and gateway transfer-events endpoints now accept `to_status` filtering and apply it at query time.
2. ~~Add contract coverage proving gateway event retrieval can isolate `FAILED` terminal events from mixed histories via `to_status` filtering.~~ ✓ Done — gateway contract tests assert `to_status=FAILED` returns only failed terminal events for both ledger submission and reversal failure flows; suites green: 24 orchestrator + 15 gateway + 31 contract tests.

Immediate next implementation sequence:
1. ~~Add combined transfer-events filter support (`event_type` + `to_status` together) validation with explicit invalid-value handling for `to_status` at the gateway boundary.~~ ✓ Done — api-gateway now validates `to_status` against allowed transfer statuses before proxying and supports combined filter passthrough.
2. ~~Add unit and contract coverage verifying combined filters narrow results deterministically and invalid `to_status` values return a stable 422 response shape.~~ ✓ Done — gateway unit and contract coverage now assert combined filter narrowing and stable 422 responses for invalid `to_status`.

Immediate next implementation sequence:
1. ~~Add client-app event filtering controls in the transfer details panel so operators can filter by failure event type and terminal status without manual query-string edits.~~ ✓ Done — client-app detail panel now provides event-type and terminal-status filter controls wired to gateway event query parameters.
2. ~~Add a lightweight server-side event summary/counts endpoint for ops dashboards so clients can render filter chips with counts without fetching the full event history.~~ ✓ Done — added `/v1/transfers/{transfer_id}/events/summary` in orchestrator and gateway passthrough, and client-app renders summary chips from server counts; suites green: 25 orchestrator + 17 gateway + 33 contract tests.

Immediate next implementation sequence:
1. ~~Add paginated transfer-events retrieval (`limit` + cursor) so large histories can be loaded incrementally without long payloads.~~ ✓ Done — orchestrator transfer-events now supports `limit` + `cursor` and emits `X-Next-Cursor`; api-gateway forwards both query params and cursor header.
2. ~~Add unit and contract coverage proving gateway passthrough preserves event ordering and cursor semantics across multi-page event histories.~~ ✓ Done — added orchestrator unit, gateway unit, and contract pagination tests validating ordered, non-overlapping pages and cursor progression; suites green: 26 orchestrator + 18 gateway + 34 contract tests.

Immediate next implementation sequence:
1. ~~Add client-app incremental event loading (`Load more events`) that uses paginated transfer-events cursors instead of refetching the full event list on each detail refresh.~~ ✓ Done — client-app detail view now fetches events with paginated cursors and appends pages via `Load more events`.
2. ~~Add client-app integration tests (or lightweight unit tests for state reducers/helpers) verifying event pagination appends in order, de-duplicates, and resets correctly when filters change.~~ ✓ Done — added lightweight Node tests for event-feed append ordering, deduplication by `event_id`, and filter-change reset detection; `node --test services/client-app/src/eventFeedState.test.js` passes (3/3).

Immediate next implementation sequence:
1. ~~Add date-range filtering for transfer history and event timelines so customers can narrow long histories without relying only on status filters.~~ ✓ Done — `created_at_from`/`created_at_to` params added to orchestrator service+routes, gateway passthrough, `api.js`, and date inputs in `index.html`; 27 orchestrator + 19 gateway + 35 contract tests green; `didEventFiltersChange` extended and 4/4 JS tests pass.
2. ~~Add deep-linkable transfer detail selection in client-app so a specific transfer can be opened directly from a shared URL or support workflow.~~ ✓ Done — `?transfer=<id>` param written to URL on selection via `history.replaceState`, read on boot to auto-select; `deepLink.js` module with `getDeepLinkTransferId`/`buildDeepLinkUrl` helpers; 4/4 unit tests in `deepLink.test.js` pass.

Immediate next implementation sequence:
1. ~~Add transfer note/memo display and inline edit in the detail view so support teams and users can annotate transfers for clarification.~~ ✓ Done — added orchestrator `PATCH /v1/transfers/{transfer_id}/note`, gateway passthrough, client inline note editor, and end-to-end note update coverage; suites green: 28 orchestrator + 20 gateway + 36 contract.
2. ~~Add transfer export (CSV download) for the visible filtered list so users and operators can pull records out of the app without querying the API directly.~~ ✓ Done — added client-side CSV export for the currently visible filtered transfer list with dedicated `transferExport.js` helper and 2 unit tests; combined client helper tests now pass: 10/10.

Immediate next implementation sequence:
1. ~~Add transfer detail copy/share actions (copy transfer ID, recipient, and deep-link URL) so support workflows can move faster from the detail pane.~~ ✓ Done — added client detail actions for copying transfer ID, recipient, and deep-link URL plus native share fallback behavior using `transferDetailActions.js`; helper tests included and passing.
2. ~~Add saved filter presets for transfer history and event timelines so frequent operator views can be restored with one click.~~ ✓ Done — added localStorage-backed transfer and event filter presets with save/apply/delete controls and `filterPresets.js`; client helper suite now passes 15/15.

Immediate next implementation sequence:
1. ~~Add transfer timeline search/filter by free-text failure reason and note content so operators can isolate problematic transfers faster.~~ ✓ Done — added backend `q` search on transfer note/failure reason in orchestrator + gateway, client transfer search input, and client-side event timeline search over event/failure text; suites green: 29 orchestrator + 21 gateway + 37 contract, plus 20 client helper tests.
2. ~~Add lightweight empty-state guidance and one-click sample preset shortcuts so first-time users discover filters and detail actions without trial and error.~~ ✓ Done — transfer/event empty states now explain next steps and sample views; added one-click shortcut buttons for common transfer and event investigations, integrated with existing filter/preset flows.

Immediate next implementation sequence:
1. ~~Add inline transfer list highlighting for matched free-text terms so operators can see why a transfer matched without opening every detail pane.~~ ✓ Done — transfer cards now show inline highlighted note/failure match context via `transferSearchHighlight.js`, so free-text search results explain themselves without opening the detail pane.
2. ~~Add lightweight client-side keyboard shortcuts for common support actions (copy ID, copy link, reload details, apply saved preset) to speed up repeated workflows.~~ ✓ Done — added `Alt+Shift+I` copy ID, `Alt+Shift+L` copy link, `Alt+Shift+R` reload details, and `Alt+Shift+P` apply selected preset using `keyboardShortcuts.js`; client helper suite now passes 25/25.

Immediate next implementation sequence:
1. ~~Add transfer detail event export (CSV/JSON) for the currently filtered event timeline so support can attach exact audit trails to cases.~~ ✓ Done — detail view now exports the currently filtered event timeline as CSV or JSON via `eventExport.js` and toolbar export actions.
2. ~~Add compact timeline density controls (comfortable/compact) and sticky detail actions so long event histories remain usable during investigations.~~ ✓ Done — added comfortable/compact density toggles, active-state button styling, and sticky detail header/copy action rows for long investigation sessions.

Immediate next implementation sequence:
1. ~~Enhance timeline JSON export with case-ready metadata (transfer ID, applied filters, generated timestamp, event count) so exports are self-describing in support workflows.~~ ✓ Done — `buildTransferEventsJson()` now emits a metadata envelope and export actions pass selected transfer ID + active filters + generated timestamp.
2. ~~Persist timeline density preference across sessions so operators keep their chosen comfortable/compact mode after reloads.~~ ✓ Done — event density mode now reads/writes `ebank.client.event-density` in localStorage and restores on app boot.

Immediate next implementation sequence:
1. ~~Add event timeline sort controls (oldest/newest) in transfer details so investigators can switch chronology without changing backend query defaults.~~ ✓ Done — added oldest/newest controls in the events toolbar, wired client-side event ordering with deterministic timestamp+event ID sorting, and persisted preference via `ebank.client.event-sort`.
2. ~~Add one-click copy for a filtered timeline digest so support can paste a concise audit narrative into case systems without downloading files.~~ ✓ Done — added `Copy digest` action that copies the currently visible filtered/sorted timeline as numbered plain text; covered by `eventDigest.test.js`.

Immediate next implementation sequence:
1. ~~Add day-grouped timeline rendering in transfer details so long histories are easier to scan across investigation windows.~~ ✓ Done — events are now rendered with date separator rows using `eventTimelineLayout.js`, while preserving existing filter/sort behavior.
2. ~~Add a live visible/total event counter in the timeline toolbar so operators can immediately see filter impact without manual counting.~~ ✓ Done — toolbar now shows `shown of total` counts that update on filter/search/sort changes and reset cleanly when selection changes.

Immediate next implementation sequence:
1. ~~Add quick event date-range shortcuts (last 24h/7d/30d) so investigators can scope timelines in one click without manually setting both date inputs.~~ ✓ Done — added timeline date shortcut buttons wired via `eventDateShortcuts.js` to populate and apply rolling ranges.
2. ~~Persist event filter state (type/status/search/date range) across reloads so investigation context survives session refreshes.~~ ✓ Done — event filters now read/write through `eventFilterState.js` and are restored on boot before detail loads.

Immediate next implementation sequence:
1. ~~Add active event-filter chips with one-click removal so operators can see and adjust current scope without reopening each control.~~ ✓ Done — active filters now render as removable chips (`eventFilterShare.js`) that clear individual criteria and reload the timeline.
2. ~~Add one-click copy of the current event-filter query string so support teams can share reproducible investigation scope in tickets and chat.~~ ✓ Done — added `Copy filters` action that copies the active timeline filter query string from current UI state.

Immediate next implementation sequence:
1. ~~Add a one-click clear-all action in active event-filter chips so investigators can reset scope quickly after exploratory filtering.~~ ✓ Done — active filter chip row now includes a `Clear all` chip when multiple filters are active, wired to reset all event filters.
2. ~~Extend keyboard shortcuts for event investigations (copy filters, copy digest, newest/oldest sort) so repeated timeline workflows are faster without mouse travel.~~ ✓ Done — added `Alt+Shift+F` copy filters, `Alt+Shift+D` copy digest, `Alt+Shift+N` newest-first sort, and `Alt+Shift+O` oldest-first sort with updated shortcut tests.

Immediate next implementation sequence:
1. ~~Add a sticky `Failed only` event toggle in the timeline actions so investigators can pivot to terminal failures without opening status filters.~~ ✓ Done — added `Failed only` action button that toggles `toStatus=FAILED` on/off from current event filter state.
2. ~~Add an optional auto-apply mode for event filters so filter edits can refresh timeline results immediately without pressing Apply each time.~~ ✓ Done — added persisted `Auto apply` toggle (localStorage-backed) with debounced input/change listeners for event filter controls.

Immediate next implementation sequence:
1. ~~Add keyboard shortcuts for fast filter resets/pivots (`clear filters`, `toggle failed-only`) so investigators can iterate timeline scope without leaving the keyboard.~~ ✓ Done — added `Alt+Shift+C` clear event filters and `Alt+Shift+X` toggle failed-only mode, wired through the global shortcut handler.
2. ~~Add inline event shortcut hint text near timeline controls so operators can discover the expanded key bindings without external docs.~~ ✓ Done — added an inline shortcut hint strip in the timeline controls showing core event investigation key combos.

Immediate next implementation sequence:
1. ~~Add a markdown-formatted failure handoff summary so support teams can paste structured incident context directly into issue trackers and postmortems without reformatting plain text exports.~~ ✓ Done — added `eventFailureMarkdown.js` and `Copy failure markdown` action that copies a markdown summary containing transfer, counts, failure rate, filters, failed IDs, and failed timeline bullets.
2. ~~Add a keyboard shortcut for markdown failure summary copy to keep high-tempo incident triage fully keyboard-driven.~~ ✓ Done — added `Alt+Shift+M` mapping (`copy-failure-markdown`) with handler wiring and shortcut hint update.

Immediate next implementation sequence:
1. ~~Add a downloadable failure snapshot report artifact (plain text) so investigators can attach a durable case file to tickets without manual copy-paste and formatting drift.~~ ✓ Done — added `eventFailureReport.js` and `Download failure report` action that exports transfer-scoped failure summary, filter query, failed IDs, and failed timeline rows as `.txt`.
2. ~~Add a keyboard shortcut for failure report download to keep escalation flow keyboard-first during active incident triage.~~ ✓ Done — added `Alt+Shift+B` mapping (`download-failure-report`) with handler wiring and shortcut hint update.

Immediate next implementation sequence:
1. ~~Add a copyable failure snapshot artifact (counts, rate, failed IDs, and active filter query) so incident handoff can be pasted into tickets and chat without manual assembly.~~ ✓ Done — added `eventFailureSnapshot.js` and `Copy failure snapshot` action that copies transfer-scoped visible-event counts, failed counts, failure rate, failed IDs, and filter query string.
2. ~~Add a keyboard shortcut for failure snapshot copy to reduce friction during active investigations where support operators stay on keyboard.~~ ✓ Done — added `Alt+Shift+S` mapping (`copy-failure-snapshot`) with handler wiring and updated inline shortcut hint.

Immediate next implementation sequence:
1. ~~Add an inline failure-rate indicator in the timeline toolbar so investigators can quantify incident concentration at a glance under the current filtered/sorted event scope.~~ ✓ Done — added `eventFailureRate` label (`Failure rate X%`) recalculated on each event render from visible failed vs visible total events.
2. ~~Add one-click copy of failed event IDs for rapid escalation handoff (ticket titles, incident chats, and runbook references) without manual row scanning.~~ ✓ Done — added `Copy failed IDs` action and `Alt+Shift+U` shortcut, backed by `eventFailureInsights.js` (`getFailedEventIds`, `buildFailedEventIdsText`) and unit tests.

Immediate next implementation sequence:
1. ~~Add verification lifecycle timestamping in alias-service so successful OTP verification records include a durable `verified_at` audit field for downstream support/compliance workflows.~~ ✓ Done — `PhoneVerification` now persists nullable `verified_at`, verify flow sets it on first successful OTP match, and `/v1/aliases/verify-phone` returns it in `VerifyPhoneResponse`.
2. ~~Expand alias domain status taxonomy with explicit `VERIFIED` state so the model reflects pre-bind lifecycle semantics and future policy routing without enum churn.~~ ✓ Done — `AliasStatus` now includes `VERIFIED`; API test coverage added for `verified_at` lifecycle (`test_verify_phone_sets_verified_at_on_success`) and alias-service suite remains green.

Immediate next implementation sequence:
1. ~~Add a live failed-events visible counter beside the existing timeline visibility counter so investigators can instantly gauge failure density under current filters/sort without opening summary chips.~~ ✓ Done — added `eventFailedCount` in the toolbar, updated on every timeline render using currently visible events.
2. ~~Add one-click copy for a failed-only timeline digest so support can paste just incident-relevant events into case notes without manual filtering/export steps.~~ ✓ Done — added `Copy failed digest` action plus `Alt+Shift+Y` shortcut, backed by `eventFailureDigest.js` to copy only failure-related events (FAILED status, FAILED event types, or events with `failure_reason`).

Immediate next implementation sequence:
1. ~~Add timeline actions to jump directly between failed events in the currently visible filtered timeline so investigators can triage incidents without stepping through non-failure rows.~~ ✓ Done — added `Prev failed` / `Next failed` controls that navigate across failure-related events (FAILED status, FAILED event types, or events with `failure_reason`) with wrap-around and auto-scroll.
2. ~~Add keyboard shortcuts for failed-event stepping so support can move across failure checkpoints without pointer interaction during high-volume investigations.~~ ✓ Done — added `Alt+Shift+Q` (previous failed) and `Alt+Shift+W` (next failed), wired through the global shortcut handler and shortcut hint.

Immediate next implementation sequence:
1. ~~Add timeline toolbar controls to jump to previous/next visible event while keeping inline detail expansion in sync, so investigators can step through long histories without repeated pointer travel.~~ ✓ Done — added `Prev event` / `Next event` actions that move the expanded row across the current filtered+sorted visible timeline (with wrap-around), keep one expanded row active, and auto-scroll it into view.
2. ~~Add keyboard shortcuts for expanded-event stepping so support users can navigate event-by-event entirely from the keyboard during investigations.~~ ✓ Done — added `Alt+Shift+J` (previous event) and `Alt+Shift+K` (next event) mappings, wired through the global shortcut handler and reflected in the inline shortcut hint.

Immediate next implementation sequence:
1. ~~Add collapsible per-event inline detail strip to the transfer events timeline so investigators can expand a single row to see all event fields (event_id, type, from/to status, failure reason, full ISO timestamp) without opening a separate view.~~ ✓ Done — clicking an event row in the timeline toggles an inline detail panel via `buildEventRowDetailHtml()`; only one row is expanded at a time and expansion resets when a new transfer is selected.
2. ~~Add a per-event copy button so support can copy a compact structured text representation of any single event to the clipboard instantly during an investigation.~~ ✓ Done — each event row shows a hover-revealed copy icon (via `buildEventRowCopyText()` in `eventRowDetail.js`) that writes pipe-separated event fields and fires a toast; 48/48 client tests passing.
1. ~~Sync active event filters into URL query params so current investigation scope remains shareable and browser-refresh safe.~~ ✓ Done — event filter state now updates URL params (`evType`, `evStatus`, `evFrom`, `evTo`, `evQ`) on each filter apply while preserving existing query params.
2. ~~Restore event filters from URL on boot (overriding stored local filters when present) so shared links reopen exact timeline scope reliably.~~ ✓ Done — added URL filter parsing on startup and precedence over localStorage filters when URL filter params are present.

Immediate next implementation sequence:
1. ~~Add `PATCH /v1/aliases/{alias_id}/discoverable` endpoint to the alias-service so users can toggle alias discoverability without unbinding, enabling privacy-safe alias discovery controls (Epic C2).~~ ✓ Done — added `UpdateDiscoverableRequest` schema, `update_discoverable()` service method, `AliasMustBeBoundError`, and `PATCH /v1/aliases/{alias_id}/discoverable` route; returns 404 for unknown alias, 409 for non-BOUND alias.
2. ~~Add durable unbind audit fields (`unbound_at`, `unbound_reason`) to the `Alias` model so every unbind operation has a compliance-ready timestamp and reason code for downstream support and audit workflows (Epic C3).~~ ✓ Done — `unbound_at` and `unbound_reason` persisted on `Alias` during `unbind_alias()`, exposed in `AliasResponse`; 4 new API tests added; alias-service suite green: 7 tests passing.

Immediate next implementation sequence:
1. ~~Add a timeline action to copy the currently expanded event detail so investigators can capture full per-event context without aiming for the tiny row-level copy icon during rapid triage.~~ ✓ Done — added `Copy expanded event` toolbar action wired to the currently expanded visible event and guarded with clear empty-state toasts when no row is expanded.
2. ~~Add a keyboard shortcut for expanded-event copy so event-by-event investigations stay keyboard-first after navigation (`J/K`, `Q/W`).~~ ✓ Done — added `Alt+Shift+E` mapping (`copy-expanded-event`), handler wiring, updated shortcut hint text, and helper/test coverage (`buildExpandedEventCopyText`); client suite green: 68 tests passing.

Immediate next implementation sequence:
1. ~~Add a timeline toolbar action to collapse the currently expanded event detail so investigators can quickly reset row focus after stepping through events.~~ ✓ Done — added `Collapse event` action that clears the expanded row in-place with guardrails for no-transfer/no-expanded states.
2. ~~Add a keyboard shortcut for collapse (`Alt+Shift+Z`) so investigators can keep event navigation and detail toggling fully keyboard-driven.~~ ✓ Done — added `collapse-expanded-event` shortcut mapping and handler wiring, updated inline shortcut hint, and extended shortcut tests; client suite remains green: 68 tests passing.

Immediate next implementation sequence:
1. ~~Add timeline actions to jump directly to the first visible event and the most recent visible event so investigators can anchor quickly at the start or end of long filtered timelines.~~ ✓ Done — added `First event` and `Latest event` toolbar actions that expand and scroll to boundary events in the current visible ordering.
2. ~~Add keyboard shortcuts for boundary event jumps so investigators can move to timeline anchors without pointer travel.~~ ✓ Done — added `Alt+Shift+A` (`event-expand-first`) and `Alt+Shift+G` (`event-expand-last`) mappings, handler wiring, and shortcut-hint updates; added `getBoundaryEventId()` helper + tests; client suite green: 69 tests passing.
3. ~~Add toolbar actions and keyboard shortcuts to jump directly to the first or latest failure event so investigators can skip to the fault boundary without scrolling.~~ ✓ Done — added `First failed` and `Latest failed` toolbar buttons, `Alt+Shift+H` (`failure-expand-first`) and `Alt+Shift+T` (`failure-expand-last`) mappings, `getBoundaryFailureEventId()` helper + 4 tests, full `main.js` wiring (DOM refs, sync, action function, listeners, dispatch); client suite green: 70 tests passing.

Immediate next implementation sequence:
1. ~~Add recycled-number detection to `bind_alias` so that when a phone number is rebound to a different user after being unbound, the new alias row records `recycled_from_user_id` and `recycled_at` for durable compliance audit (Epic C3).~~ ✓ Done — `bind_alias` now queries the most recent UNBOUND alias for the phone; if its `user_id` differs from the incoming request, the new `Alias` row is stamped with `recycled_from_user_id` and `recycled_at`; same-user rebind produces no recycled fields.
2. ~~Add `GET /v1/aliases/history/{phone_e164}` endpoint returning the full chronological binding history for a phone number so compliance teams can audit the complete owner chain and detect recycled-number scenarios before initiating transfers.~~ ✓ Done — added `get_alias_history()` service method, `AliasHistoryResponse` schema (`phone_e164`, `total`, `aliases[]`), and `GET /v1/aliases/history/{phone_e164}` route; 5 new tests covering same-user rebind, different-user rebind, ordered history, empty phone, and single binding; alias-service suite green: 12 tests passing.

Immediate next implementation sequence:
1. ~~Add `GET /v1/aliases/{alias_id}` direct alias fetch endpoint so compliance and support tooling can retrieve an alias record by ID without requiring a phone number or full history scan.~~ ✓ Done — added `get_alias_by_id()` service method and `GET /v1/aliases/{alias_id}` route; returns 404 for unknown IDs.
2. ~~Add `ResolveAuditLog` model and `GET /v1/aliases/audit/resolve` endpoint so every alias resolve call is durably recorded (phone, caller identity, result_found, timestamp) and queryable for anti-enumeration monitoring (Epic C2).~~ ✓ Done — `ResolveAuditLog` table persists one row per resolve call; `resolve_alias()` accepts and logs `X-Caller-Id` header; `GET /v1/aliases/audit/resolve?phone_e164=&limit=` returns pageable audit entries; `ResolveAuditEntry` + `ResolveAuditResponse` schemas added; 5 new tests covering direct lookup 200/404, audit entry with caller, not-found audit, and limit param; alias-service suite green: 17 tests passing.

Immediate next implementation sequence:
1. ~~Add caller-based anti-enumeration throttling on `GET /v1/aliases/resolve` so repeated not-found lookups from the same caller are rate-limited before they can scan large phone ranges (Epic C2).~~ ✓ Done — resolve calls now count recent unblocked misses per caller over a 60-minute window and return 429 after the third miss; anonymous callers are bucketed as `anonymous`; blocked attempts are still logged for audit.
2. ~~Add `GET /v1/aliases/audit/resolve/summary` so operations can inspect aggregate resolve behavior per caller (`total`, `found`, `not_found`, `blocked`) without manually scanning raw audit rows.~~ ✓ Done — added `ResolveAuditSummaryResponse`, blocked flag on `ResolveAuditLog`, and summary aggregation by caller ID; anti-enumeration coverage added for named callers, anonymous callers, safe successful lookups, and summary counts.

Immediate next implementation sequence:
1. ~~Add caller and time-window filters to `GET /v1/aliases/audit/resolve` so compliance and anti-enumeration tooling can inspect recent lookup activity without scanning the full audit table or only querying by phone.~~ ✓ Done — raw resolve audit now supports `caller_id` and `window_minutes` filters, returns applied filters in the response, and rejects unscoped queries unless `phone_e164` or `caller_id` is provided.
2. ~~Add `GET /v1/aliases/audit/resolve/callers` recent-caller leaderboard endpoint so operators can quickly identify the busiest or most-blocked lookup sources over a rolling window.~~ ✓ Done — added per-caller recent aggregation (`total`, `found`, `not_found`, `blocked`, `latest_at`) with `window_minutes`, `limit`, and `blocked_only` filters; tests cover caller filtering, old-entry exclusion, leaderboard membership, and blocked-only output.

Immediate next implementation sequence:
1. ~~Add `status` filtering to `GET /v1/aliases/history/{phone_e164}` so support and compliance teams can isolate only active (`BOUND`) or released (`UNBOUND`) bindings when reviewing a number’s ownership chain.~~ ✓ Done — history endpoint now accepts `status=BOUND|UNBOUND|VERIFIED`, validates invalid values with a stable 422, and echoes the applied status filter in the response.
2. ~~Add `GET /v1/aliases/recycled` endpoint so teams can list recycled-number bindings directly, optionally filtered by current `user_id`, without scanning individual phone histories one by one.~~ ✓ Done — added recycled binding listing ordered by latest recycle timestamp with `user_id` and `limit` filters; tests cover recycled-only output, user filtering, and limit behavior.

Immediate next implementation sequence:
1. ~~Enforce `discoverable=false` in `GET /v1/aliases/resolve` so public alias lookup respects the privacy control instead of returning any bound alias regardless of discoverability (Epic C2).~~ ✓ Done — public resolve now only returns aliases with `status=BOUND` and `discoverable=true`; hidden aliases remain invisible to public lookups while still being audit-logged as misses.
2. ~~Add `GET /v1/aliases/undiscoverable` endpoint so support/compliance can list currently hidden bound aliases, optionally filtered by `user_id`, without bypassing privacy through the public resolve flow.~~ ✓ Done — added undiscoverable alias listing ordered by latest update time with `user_id` and `limit` filters; tests cover public resolve privacy, direct fetch of hidden aliases, and undiscoverable listing/filter behavior.

Immediate next implementation sequence:
1. ~~Add an internal alias resolve path that can intentionally return undiscoverable aliases for support/compliance workflows, while still requiring explicit caller identity and purpose metadata for auditability (Epic C2).~~ ✓ Done — added `GET /v1/aliases/resolve/internal` requiring `X-Caller-Id` and `purpose`; internal resolve can include hidden aliases without weakening the public resolve path.
2. ~~Extend resolve-audit records and filtering with lookup scope/purpose so investigators can distinguish public lookups from internal support/compliance access when reviewing alias-resolution activity.~~ ✓ Done — `ResolveAuditLog` now stores `lookup_scope` and `purpose`; audit responses expose both fields and `GET /v1/aliases/audit/resolve` supports `lookup_scope=PUBLIC|INTERNAL` filtering with 422 validation for invalid values.

Immediate next implementation sequence:
1. ~~Introduce a controlled internal resolve purpose taxonomy so support/compliance lookups cannot use arbitrary free-form purpose strings and downstream reporting stays consistent (Epic C2).~~ ✓ Done — internal resolve now validates `purpose` against an allowed set (`support-review`, `compliance-review`, `fraud-investigation`, `dispute-review`) and returns 422 for invalid values.
2. ~~Add `GET /v1/aliases/audit/resolve/purposes` purpose-summary endpoint so teams can monitor which internal purposes drive hidden-alias lookups over a rolling window.~~ ✓ Done — added purpose-level aggregate reporting (`total`, `found`, `not_found`, `blocked`, `latest_at`) with `lookup_scope`, `window_minutes`, and `limit` filters; tests cover valid summaries and invalid scope validation.

Immediate next implementation sequence:
1. ~~Introduce a controlled unbind-reason taxonomy so alias lifecycle release events use consistent reason codes instead of arbitrary free-form values, improving downstream compliance reporting (Epic C3).~~ ✓ Done — `UnbindAliasRequest.reason_code` now validates against an allowed set (`user-request`, `compliance-hold`, `number-change`, `rotate`, `reassign`, `move`) and invalid values return 422.
2. ~~Add `GET /v1/aliases/audit/unbind-reasons` summary endpoint so compliance can monitor why aliases are being released over a rolling window without scanning full alias histories.~~ ✓ Done — added unbind-reason aggregation (`reason_code`, `total`, `latest_at`) with `window_minutes` and `limit` filters; tests cover invalid reason rejection, summary counts, and old-entry exclusion.

Immediate next implementation sequence:
1. ~~Introduce a controlled discoverability-change reason taxonomy so privacy visibility changes use consistent reason codes instead of free-form notes, improving downstream compliance reporting (Epic C2).~~ ✓ Done — `PATCH /v1/aliases/{alias_id}/discoverable` now requires a validated `reason_code` (`privacy-request`, `support-guided`, `fraud-review`, `compliance-review`) and persists discoverability change metadata on the alias record.
2. ~~Add `GET /v1/aliases/audit/discoverability-reasons` summary endpoint so compliance can monitor why alias visibility is changing over a rolling window without scanning individual alias records.~~ ✓ Done — added discoverability-change aggregation (`reason_code`, `total`, `latest_at`) with `window_minutes` and `limit` filters; tests cover invalid reason rejection, summary counts, and old-entry exclusion.

Immediate next implementation sequence:
1. ~~Add raw unbind-audit query support so compliance and support tooling can retrieve filtered alias-unbind events by `user_id` and `reason_code` without scanning all alias records manually (Epic C3).~~ ✓ Done — added `GET /v1/aliases/audit/unbind` with `user_id`, `reason_code`, `window_minutes`, and `limit` filters returning ordered unbind audit events.
2. ~~Add `GET /v1/aliases/audit/unbind/users` user-level summary endpoint so operators can quickly identify accounts with unusual unbind activity over a rolling window.~~ ✓ Done — added per-user unbind aggregates (`total`, `latest_at`) with `window_minutes` and `limit` filters; tests cover filtered audit retrieval, summary counts, and old-entry exclusion.

Immediate next implementation sequence:
1. ~~Add phone-number level filtering to raw lifecycle audit endpoints so investigations can pivot by `phone_e164` directly when reviewing unbind or discoverability-change events (Epic C2/C3).~~ ✓ Done — added `phone_e164` to lifecycle audit logs and exposed `phone_e164` filters on `GET /v1/aliases/audit/unbind` and `GET /v1/aliases/audit/discoverability`; responses now echo the applied phone filter and include phone on each audit entry.
2. ~~Persist `phone_e164` directly on lifecycle audit log rows so audit queries remain efficient and do not require joining back to mutable alias rows for basic phone-based analysis.~~ ✓ Done — added indexed `phone_e164` columns to `UnbindAuditLog` and `DiscoverabilityAuditLog`, populated at write-time; added test coverage for phone-filtered unbind/discoverability audit retrieval.

Immediate next implementation sequence:
1. ~~Add raw discoverability-audit query support so compliance and support tooling can retrieve filtered visibility-change events by `user_id` and `reason_code` without scanning all aliases manually (Epic C2).~~ ✓ Done — added `GET /v1/aliases/audit/discoverability` with `user_id`, `reason_code`, `window_minutes`, and `limit` filters, returning ordered discoverability audit events with full metadata.
2. ~~Add `GET /v1/aliases/audit/discoverability/users` user-level summary endpoint so operators can quickly identify accounts with unusual visibility-toggle activity over a rolling window.~~ ✓ Done — added per-user discoverability aggregates (`total`, `visible_enabled`, `visible_disabled`, `latest_at`) with `window_minutes` and `limit` filters; tests cover filtered audit retrieval, user summary counts, and old-entry exclusion.

Immediate next implementation sequence:
1. ~~Add optional `reason_code` filtering to lifecycle summary endpoints (`/audit/unbind-reasons` and `/audit/discoverability-reasons`) so compliance can isolate one policy bucket without post-processing all categories client-side.~~ ✓ Done — both summary endpoints now accept `reason_code`, apply server-side filtering, and echo the applied filter in the response.
2. ~~Add a consolidated `GET /v1/aliases/audit/lifecycle/summary` endpoint so investigators can retrieve unbind and discoverability aggregates together for a given `phone_e164` and/or `user_id` in a single request.~~ ✓ Done — added combined lifecycle summary response with `unbind_total`, `unbind_by_reason`, `discoverability_total`, and `discoverability_by_reason`, plus `phone_e164`/`user_id` scoping.

Immediate next implementation sequence:
1. ~~Add bearer token extraction and validation for API Gateway authentication so all external callers must provide OAuth2-style Authorization headers with cryptographically valid tokens.~~ ✓ Done — added `TokenValidator` in `app/domain/token_validator.py` supporting token extraction from Authorization header, SHA256-based test token generation, token revocation tracking, and basic known token validation for development (service/admin/user token types).
2. ~~Add authentication middleware enforcing bearer token requirement on protected `/v1/*` routes with configurable enforcement via `ENFORCE_AUTHENTICATION` setting so both integration tests and production deployments can be controlled.~~ ✓ Done — `AuthenticationMiddleware` added in `app/middleware/authentication.py` with request identity extraction, per-request state management, unprotected route bypass (health, docs), configurable middleware addition in `main.py`. Request identity with caller ID, type, and permissions is now stored in `request.state.identity` and propagated to downstream services via `X-Caller-Id`, `X-Caller-Type`, `X-Caller-Permissions` headers; test suite enhanced with conftest setting `ENFORCE_AUTHENTICATION=false` for test compatibility.
Pair 8 completion summary: Full auth infrastructure for API Gateway (40 tests passing: 19 auth-specific + 21 gateway regression tests); bearer token extraction, known-token database, revocation tracking, request identity propagation; production-ready with configurable enforcement toggle.

Immediate next implementation sequence:
1. ~~Add route-level authorization checks in API Gateway so authenticated identities must also carry endpoint-appropriate permissions (for example `transfer:create`, `reconciliation:run`, `alias:manage`) before requests are forwarded upstream.~~ ✓ Done — added `_authorize()` in `app/api/routes.py` with centralized permission enforcement and stable `401`/`403` error semantics, then wired permission checks across transfer, connector, reconciliation, identity, and alias gateway routes.
2. ~~Add configurable authorization enforcement toggle and regression coverage so existing test and local-dev workflows can disable strict permission checks while production retains strict policy enforcement.~~ ✓ Done — added `ENFORCE_AUTHORIZATION` setting in `app/config.py`, test bootstrap now disables both auth and authorization in `tests/conftest.py`, and new auth suite coverage validates `_authorize()` success/401/403 behavior plus identity header forwarding.
Pair 9 completion summary: API Gateway now enforces both authentication and route-level authorization with explicit permission taxonomy expansion for identity operations (`identity:create_user`, `identity:view_user`, `identity:submit_kyc`); full gateway suite green at 43 passing tests.

Immediate next implementation sequence:
1. ~~Add gateway-side authorization decision audit logging so every permission check records caller, endpoint, required permission, allow/deny result, reason, request ID, and timestamp for post-incident security review.~~ ✓ Done — added `AuthorizationAuditStore` in `app/domain/authorization_audit.py`; route-level `_authorize()` now records both allow and deny decisions (`authorized`, `missing_identity`, `missing_permission`) with request metadata.
2. ~~Add an admin query endpoint for authorization audit records with caller/outcome/window filters so security/compliance teams can inspect access behavior without log scraping.~~ ✓ Done — added `GET /v1/auth/audit/authorization` with `caller_id`, `allowed`, `window_minutes`, and `limit` filters, protected by `auth:view_audit` permission; admin token now includes this permission.
Pair 10 completion summary: Authorization checks are now observable via an in-memory audit stream and query API; targeted + full gateway suites are green at 44 passing tests.

Immediate next implementation sequence:
1. ~~Build a standalone risk-service (FastAPI + SQLAlchemy/SQLite) with a configurable rule engine and evaluation audit log so risk decisions are decoupled from the orchestrator and can be managed at runtime.~~ ✓ Done — `services/risk-service` scaffolded with `RiskRule` + `RiskEvaluationLog` models, first-match-wins rule evaluator, rule CRUD endpoints (`POST/GET/DELETE /v1/risk/rules`), evaluation endpoint (`POST /v1/risk/evaluate`), and evaluation audit log query (`GET /v1/risk/log`); 21 tests passing.
2. ~~Wire the payment-orchestrator to call the standalone risk-service via an HTTP client, with transparent fallback to local prechecks when the service is unreachable.~~ ✓ Done — added `app/domain/risk_client.py` to the orchestrator with `call_risk_service()` (urllib, configurable URL/timeout/enabled flag, safe fallback on any `URLError`); `run_prechecks()` now calls the client first and falls back to local rules only when service returns `None`; 10 new orchestrator tests cover allow/deny/review (remote) and allow/deny (local fallback after connection refused); full orchestrator suite green at 39 passing tests.
Pair 11 completion summary: Risk evaluation is now a standalone service with a runtime-configurable rule engine; orchestrator transparently uses it when enabled and degrades gracefully to local prechecks on failure.

Immediate next implementation sequence:
1. ~~Build a standalone compliance-service (FastAPI + SQLAlchemy/SQLite) with a configurable sanctions watchlist, Levenshtein-based fuzzy name matching (exact → HIT, near → POTENTIAL_MATCH, far → CLEAR), soft-delete watchlist management, and a full screening audit log.~~ ✓ Done — `services/compliance-service` scaffolded with `WatchlistEntry` + `ScreeningLog` models, pure-Python Levenshtein matcher, screening endpoint (`POST /v1/compliance/screen`), watchlist CRUD (`GET|POST /v1/compliance/watchlist`, `DELETE /v1/compliance/watchlist/{entry_id}`), and audit log query (`GET /v1/compliance/log`); 22 tests passing.
2. ~~Wire the identity-service KYC approval path to screen the applicant against the compliance-service; a confirmed sanctions hit overrides the operator approval to REJECTED; service unavailability applies a configurable fallback policy (allow/deny).~~ ✓ Done — added `app/domain/compliance_client.py` to identity-service (urllib, `compliance_service_enabled` gate, safe fallback on `URLError`); `decide_kyc()` calls screen on APPROVED decisions and downgrades to REJECTED on HIT; `POTENTIAL_MATCH` is advisory (does not block); deny fallback policy supported; 7 new identity-service tests cover all paths; total identity-service suite green at 9 tests.
Pair 12 completion summary: Sanctions screening is now a standalone service with fuzzy name matching and soft-delete watchlist management; KYC approval in identity-service is gated by sanctions checks with configurable fallback behaviour.

Immediate next implementation sequence:
1. ~~Add sender KYC and account-status verification into orchestrator prechecks by calling identity-service (`GET /v1/users/{user_id}/status`); block transfers if account is not ACTIVE or KYC is not APPROVED; configurable fallback policy on service unavailability.~~ ✓ Done — added `app/domain/identity_client.py` to orchestrator (urllib, `identity_service_enabled` gate, `_urlopen` module-level binding for independent patching); `run_prechecks()` performs identity check as step 1 before alias and risk checks; 7 new tests cover all account/KYC/fallback paths.
2. ~~Add recipient alias resolution check into orchestrator prechecks by calling alias-service (`GET /v1/aliases/resolve?phone_e164=...`); distinguish 404 not-found from connection error; block if alias is absent; configurable fallback policy.~~ ✓ Done — added `app/domain/alias_client.py` to orchestrator (HTTP 404 → `("","")` safe not-found signal vs URLError → None service-unavailable); `run_prechecks()` performs alias check as step 2; 9 new tests cover found/not-found/unavailable/fallback paths; all 52 orchestrator tests passing.
Pair 13 completion summary: Orchestrator prechecks now enforce a 4-step ordered gate — sender identity/KYC → recipient alias resolution → remote risk-service → local fallback rules — ensuring transfers are rejected at the earliest possible point if any upstream service signals a problem; all three HTTP clients use independent `_urlopen` module-level bindings so they can be patched in isolation during tests.

Immediate next implementation sequence:
1. ~~Expose risk-service through the API Gateway: add `RiskClient` in gateway (`app/clients/risk_client.py`), add 4 new permissions (`VIEW_RISK_RULES`, `MANAGE_RISK_RULES`, `VIEW_RISK_LOG`, `EVALUATE_RISK`), add 5 routes (`GET|POST /v1/risk/rules`, `DELETE /v1/risk/rules/{rule_id}`, `GET /v1/risk/log`, `POST /v1/risk/evaluate`) with correct permission gates and 502 on upstream 5xx.~~ ✓ Done — `app/clients/risk_client.py` scaffolded; 5 risk routes added to `api/routes.py`; 6 new gateway tests cover forwarding, payload capture, query param passthrough, and 502 propagation.
2. ~~Expose compliance-service through the API Gateway: add `ComplianceClient` in gateway (`app/clients/compliance_client.py`), add 4 new permissions (`VIEW_COMPLIANCE_WATCHLIST`, `MANAGE_COMPLIANCE_WATCHLIST`, `VIEW_COMPLIANCE_LOG`, `SCREEN_COMPLIANCE_SUBJECT`), add 5 routes (`GET|POST /v1/compliance/watchlist`, `DELETE /v1/compliance/watchlist/{entry_id}`, `GET /v1/compliance/log`, `POST /v1/compliance/screen`).~~ ✓ Done — `app/clients/compliance_client.py` scaffolded; 5 compliance routes added; 9 new gateway tests pass; gateway test suite now 59 tests total.
Pair 14 completion summary: Risk-service and compliance-service are now fully reachable via the API Gateway; all 8 newly defined permissions follow the least-privilege `domain:action` naming convention already established in the gateway; callers require distinct permissions to view vs mutate watchlist entries and to trigger a screening vs to view audit logs.

Immediate next implementation sequence:
1. ~~Add account lifecycle admin operations to identity-service: `suspend_account`, `reinstate_account`, `close_account` with valid state-machine transitions (ACTIVE→SUSPENDED, SUSPENDED→ACTIVE, ACTIVE|SUSPENDED→CLOSED); each transition is immutably logged in `AccountAuditLog` with actor ID and reason.~~ ✓ Done — added `InvalidAccountTransitionError`, `AccountAuditLog` model, `AccountStatusChangeRequest` + `AccountAuditLogEntry` schemas, `_transition_account_status()` helper in service, and 4 new routes (`POST /v1/users/{id}/suspend|reinstate|close`, `GET /v1/users/{id}/account-audit-log`); 20 new identity-service tests covering all transitions, 404/409/422 paths, actor propagation, and status reflection; total 29 identity-service tests.
2. ~~Expose the 4 new account lifecycle routes through the API Gateway with 2 new permissions (`MANAGE_ACCOUNT_STATUS`, `VIEW_ACCOUNT_AUDIT_LOG`) and 4 new client methods on `IdentityClient`; 502 on upstream 5xx.~~ ✓ Done — client methods added, routes wired, 10 new gateway tests cover forwarding/409/404/502; gateway suite now 69 tests.
Pair 15 completion summary: Operations teams can now suspend, reinstate, or permanently close accounts via the API Gateway with full audit trail; every transition is state-machine-guarded so invalid moves return 409; the actor identity (X-Caller-Id header) is captured in every audit log entry enabling accountability for every account action.

Immediate next implementation sequence:
1. ~~Expose ledger-service account and balance operations through the API Gateway: add `LedgerClient` in gateway (`app/clients/ledger_client.py`), add 3 new permissions (`CREATE_LEDGER_ACCOUNT`, `VIEW_LEDGER_BALANCE`, `VIEW_LEDGER_ENTRY`), add 3 routes (`POST /v1/ledger/accounts`, `GET /v1/ledger/accounts/{account_id}/balance`, `GET /v1/ledger/entries/{entry_id}`) with correct permission gates and 502 on upstream 5xx.~~ ✓ Done — `app/clients/ledger_client.py` created; 3 ledger permissions added; 3 routes added; 9 new gateway tests cover forwarding, payload capture, 404/409/502 paths; gateway test suite now 78 tests.
Pair 16 completion summary: Ledger account creation and balance/entry lookups are now fully exposed through the API Gateway, enabling operations teams to initialize accounts for users and transit flows, and audit/debug specific transfers via entry inspection; orchestrator already calls ledger internally when posting transfers, so this pair unblocks operational visibility into the ledger double-entry layer.

Immediate next implementation sequence:
1. ~~Add single-transfer amount limits to the payment-orchestrator by KYC tier so fraud risk is capped per-transaction at the earliest gate (step 1b of prechecks, after identity KYC check and before alias resolution).~~ ✓ Done — added `TransferLimitTier` class and `transfer_limits_by_kyc_status` dict with 4-tier config (NOT_STARTED/SUBMITTED: 10k, APPROVED: 500k, REJECTED: 0); implemented `check_transfer_limits(kyc_status, amount_minor)` with early guard for disabled limits and explicit 0-limit blocking; inserted into precheck flow as step 1b; 8 new orchestrator tests cover all tiers, disabled-limits bypass, exactly-at-limit passes, and REJECTED blocking; gateway contract and local fallback paths respect limit enforcement; 60 orchestrator tests passing.
2. ~~Add daily-transfer amount accumulation limits to the payment-orchestrator by KYC tier so velocity-based attacks are prevented through rolling-window capping (step 1c of prechecks, after single-transfer limit and before alias resolution).~~ ✓ Done — implemented `check_daily_transfer_limits(db, sender_user_id, kyc_status, amount_minor)` with UTC day bucketing (`datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)`), SQLAlchemy `func.sum()` query filtering on sender, created_at window, and status in [SETTLED, VALIDATED, RESERVED], projected-total check; config mirrors single-limit tiers (NOT_STARTED/SUBMITTED: 20k daily, APPROVED: 2M daily, REJECTED: 0); wired service layer to pass db session through transition_transfer() → run_prechecks(); 12 new tests covering single transfer under limit, accumulation across multiple transfers today, exact-at-limit passes, REJECTED blocking, UTC midnight boundary, status filtering (ignores FAILED/REVERSED), global disable bypass, and db=None defensive handling; 72 orchestrator tests passing (60 original + 8 Pair 17 + 12 Pair 18).
Pair 17 completion summary: Single-transfer limits by KYC tier prevent one-shot large frauds; integrated as step 1b of prechecks with amount validation and tier-specific caps, all enforcement guarded by global `transfer_limits_enabled` flag.
Pair 18 completion summary: Daily-transfer limits by KYC tier prevent velocity-based attacks; uses UTC day bucketing and SQLAlchemy sum-aggregation to count only SETTLED/VALIDATED/RESERVED transfers, blocking projected-total exceeding tier limit; fully integrated into orchestrator prechecks flow with db session passing from service layer, all new logic guarded by global `transfer_limits_enabled` flag and db=None defensive handling.

Immediate next implementation sequence:
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
