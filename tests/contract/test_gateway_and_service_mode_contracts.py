"""
Additional contract coverage:
1. API gateway callback-forwarding path reaches orchestrator callback logic.
2. Reconciliation in service mode executes with in-process service stubs.
3. API gateway relay path forwards to orchestrator event relay with idempotent behavior.
4. Transfer cancellation via gateway updates status to FAILED and appears correctly in transfer list.
"""

from typing import Any
import importlib


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict, headers=None):
        self.status_code = status_code
        import json

        self.content = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}


def _create_ledger_account(ledger_client, owner_id: str, account_type: str) -> str:
    resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": owner_id,
            "account_type": account_type,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201
    return resp.json()["account_id"]


def test_gateway_callback_forwarding_contract(
    gateway_client, orchestrator_client
) -> None:
    # Prepare transfer up to SUBMITTED_TO_RAIL
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-gw-1",
            "recipient_phone_e164": "+15550202020",
            "currency": "USD",
            "amount_minor": 700,
        },
        headers={"Idempotency-Key": "gw-forward-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    assert submitted.status_code == 200
    external_ref = submitted.json()["connector_external_ref"]

    # Patch gateway's internal orchestrator client to forward in-process
    callback_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/transfers/callbacks/connector"
    )
    gateway_module_globals = callback_route.endpoint.__globals__
    gateway_internal_client = gateway_module_globals["_client"]

    async def _forward_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.connector_callback = _forward_inproc

    lookup_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/transfers/{transfer_id}"
    )
    lookup_internal_client = lookup_route.endpoint.__globals__["_client"]

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(
            f"/v1/transfers/{transfer_id}",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    lookup_internal_client.get_transfer = _lookup_inproc

    # Exercise gateway callback path
    callback_resp = gateway_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
        headers={"X-Request-Id": "gw-cb-req-1"},
    )
    assert callback_resp.status_code == 200
    assert callback_resp.json()["status"] == "SETTLED"
    assert callback_resp.headers.get("X-Request-Id") == "gw-cb-req-1"

    lookup_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}",
        headers={"X-Request-Id": "gw-cb-lookup-1"},
    )
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["transfer_id"] == transfer_id
    assert lookup_resp.json()["status"] == "SETTLED"
    assert lookup_resp.json()["connector_external_ref"] == external_ref
    assert lookup_resp.headers.get("X-Request-Id") == "gw-cb-lookup-1"


def test_reconciliation_service_mode_contract(
    orchestrator_client, ledger_client, connector_client, recon_client
) -> None:
    # Prepare transfer and matching source data
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-svc-1",
            "recipient_phone_e164": "+15550303030",
            "currency": "USD",
            "amount_minor": 1300,
        },
        headers={"Idempotency-Key": "svc-mode-1"},
    )
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    external_ref = submitted.json()["connector_external_ref"]

    sender_acct = _create_ledger_account(ledger_client, "u-svc-sender", "USER_AVAILABLE")
    recv_acct = _create_ledger_account(ledger_client, "u-svc-recv", "USER_AVAILABLE")

    ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": external_ref,
            "transfer_id": transfer_id,
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": sender_acct,
                    "direction": "DEBIT",
                    "amount_minor": 1300,
                    "currency": "USD",
                },
                {
                    "account_id": recv_acct,
                    "direction": "CREDIT",
                    "amount_minor": 1300,
                    "currency": "USD",
                },
            ],
        },
    )

    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 1300,
            "currency": "USD",
            "destination": "acct-svc-1",
        },
    )
    connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )

    # Patch reconciliation service-mode readers to call in-process service clients
    run_route = next(
        r for r in recon_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs"
    )
    recon_globals = run_route.endpoint.__globals__
    ReconService = recon_globals["ReconciliationService"]
    recon_service_module = importlib.import_module(ReconService.__module__)
    recon_settings = recon_service_module.settings

    old_mode = recon_settings.source_mode
    recon_settings.source_mode = "service"

    original_ledger_reader = ReconService._read_ledger_records_from_service
    original_connector_reader = ReconService._read_connector_records_from_service

    def _ledger_reader(self):
        rows = ledger_client.get("/v1/ledger/entries").json()
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
            }
            for row in rows
        }

    def _connector_reader(self):
        rows = connector_client.get("/v1/connectors/transaction-events").json()
        latest_by_ref = {}
        for row in rows:
            latest_by_ref[row["external_ref"]] = row
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
                "status": row["status"],
                "connector_id": row["connector_id"],
            }
            for row in latest_by_ref.values()
        }

    ReconService._read_ledger_records_from_service = _ledger_reader
    ReconService._read_connector_records_from_service = _connector_reader

    try:
        run = recon_client.post("/v1/reconciliation/runs", json={})
        assert run.status_code == 201
        run_id = run.json()["run"]["run_id"]

        detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
        assert detail.status_code == 200
        mismatches_for_ref = [
            m for m in detail.json()["mismatches"] if m["external_ref"] == external_ref
        ]
        assert mismatches_for_ref == []
    finally:
        recon_settings.source_mode = old_mode
        ReconService._read_ledger_records_from_service = original_ledger_reader
        ReconService._read_connector_records_from_service = original_connector_reader


def test_gateway_event_relay_contract(gateway_client, orchestrator_client) -> None:
    # Create at least one orchestrator event
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-gw-relay-1",
            "recipient_phone_e164": "+15550404040",
            "currency": "USD",
            "amount_minor": 450,
        },
        headers={"Idempotency-Key": "gw-relay-1"},
    )
    assert create.status_code == 201

    relay_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/transfers/events/relay"
    )
    gateway_module_globals = relay_route.endpoint.__globals__
    gateway_internal_client = gateway_module_globals["_client"]

    async def _relay_inproc(limit: int, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/events/relay?limit={limit}",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.relay_events = _relay_inproc

    first = gateway_client.post("/v1/transfers/events/relay?limit=10", headers={"X-Request-Id": "gw-relay-req-1"})
    assert first.status_code == 200
    assert first.json()["exported_count"] >= 1
    assert first.headers.get("X-Request-Id") == "gw-relay-req-1"

    second = gateway_client.post("/v1/transfers/events/relay?limit=10", headers={"X-Request-Id": "gw-relay-req-2"})
    assert second.status_code == 200
    assert second.json()["exported_count"] == 0


def test_transfer_list_contract(gateway_client, orchestrator_client) -> None:
    # Create 3 transfers: 2 for user list-sender-a, 1 for list-sender-b
    for i, (sender, phone) in enumerate(
        [("list-sender-a", "+15550505050"), ("list-sender-a", "+15550505051"), ("list-sender-b", "+15550505052")],
        start=1,
    ):
        resp = orchestrator_client.post(
            "/v1/transfers",
            json={"sender_user_id": sender, "recipient_phone_e164": phone, "currency": "USD", "amount_minor": 200 + i},
            headers={"Idempotency-Key": f"list-contr-{i}"},
        )
        assert resp.status_code == 201

    # Patch gateway client to delegate list_transfers in-process to orchestrator
    list_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and "GET" in getattr(r, "methods", set())
    )
    gateway_internal_client = list_route.endpoint.__globals__["_client"]

    async def _list_inproc(params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get("/v1/transfers", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.list_transfers = _list_inproc

    # Filter by sender_user_id via gateway
    resp = gateway_client.get("/v1/transfers", params={"sender_user_id": "list-sender-a"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert all(t["sender_user_id"] == "list-sender-a" for t in data["transfers"])
    assert data["next_cursor"] is None

    # Pagination: limit=2 returns first 2 with next_cursor, second page returns the remaining 1
    page1 = gateway_client.get("/v1/transfers", params={"status": "CREATED", "limit": "2"})
    assert page1.status_code == 200
    p1 = page1.json()
    assert p1["count"] == 2
    assert p1["next_cursor"] is not None

    page2 = gateway_client.get("/v1/transfers", params={"status": "CREATED", "limit": "2", "cursor": p1["next_cursor"]})
    assert page2.status_code == 200
    p2 = page2.json()
    assert p2["count"] == 1
    assert p2["next_cursor"] is None
    # Verify no overlap between pages
    page1_ids = {t["transfer_id"] for t in p1["transfers"]}
    page2_ids = {t["transfer_id"] for t in p2["transfers"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_cancel_transfer_contract(gateway_client, orchestrator_client) -> None:
    # Create two transfers from the same sender
    tid_a = orchestrator_client.post(
        "/v1/transfers",
        json={"sender_user_id": "u-cancel-contr", "recipient_phone_e164": "+15550606060", "currency": "USD", "amount_minor": 111},
        headers={"Idempotency-Key": "cancel-contr-1"},
    ).json()["transfer_id"]
    tid_b = orchestrator_client.post(
        "/v1/transfers",
        json={"sender_user_id": "u-cancel-contr", "recipient_phone_e164": "+15550606061", "currency": "USD", "amount_minor": 222},
        headers={"Idempotency-Key": "cancel-contr-2"},
    ).json()["transfer_id"]

    # Advance tid_b to RESERVED before cancelling
    orchestrator_client.post(f"/v1/transfers/{tid_b}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{tid_b}/transition", json={"status": "RESERVED"})

    # Patch gateway cancel to delegate in-process
    cancel_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/cancel"
    )
    gateway_internal_client = cancel_route.endpoint.__globals__["_client"]

    async def _cancel_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.post(f"/v1/transfers/{transfer_id}/cancel", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.cancel_transfer = _cancel_inproc

    # Patch gateway list to delegate in-process (reuses same internal client binding)
    async def _list_inproc(params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get("/v1/transfers", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.list_transfers = _list_inproc

    # Cancel both transfers via gateway
    resp_a = gateway_client.post(f"/v1/transfers/{tid_a}/cancel", headers={"X-Request-Id": "cancel-contr-req-1"})
    assert resp_a.status_code == 200
    assert resp_a.json()["status"] == "FAILED"
    assert resp_a.json()["failure_reason"] == "CANCELLED"
    assert resp_a.headers.get("X-Request-Id") == "cancel-contr-req-1"

    resp_b = gateway_client.post(f"/v1/transfers/{tid_b}/cancel")
    assert resp_b.status_code == 200
    assert resp_b.json()["status"] == "FAILED"
    assert resp_b.json()["failure_reason"] == "CANCELLED"

    # Cancelling an already-cancelled (FAILED) transfer must return 409
    retry = gateway_client.post(f"/v1/transfers/{tid_a}/cancel")
    assert retry.status_code == 409

    # List with status=FAILED should show both cancelled transfers
    list_resp = gateway_client.get("/v1/transfers", params={"sender_user_id": "u-cancel-contr", "status": "FAILED"})
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["count"] == 2
    assert all(t["failure_reason"] == "CANCELLED" for t in listed["transfers"])

    # List with status=CREATED should return empty (no more pendng transfers)
    active_resp = gateway_client.get("/v1/transfers", params={"sender_user_id": "u-cancel-contr", "status": "CREATED"})
    assert active_resp.json()["count"] == 0


def test_gateway_transfer_events_passthrough_contract(gateway_client, orchestrator_client) -> None:
    # Settled transfer flow
    settled_create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-events-settled",
            "recipient_phone_e164": "+15550707070",
            "currency": "USD",
            "amount_minor": 777,
        },
        headers={"Idempotency-Key": "events-settled-1"},
    )
    assert settled_create.status_code == 201
    settled_id = settled_create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{settled_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{settled_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{settled_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    external_ref = submitted.json()["connector_external_ref"]
    orchestrator_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )

    # Cancelled transfer flow
    cancelled_create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-events-cancelled",
            "recipient_phone_e164": "+15550707071",
            "currency": "USD",
            "amount_minor": 555,
        },
        headers={"Idempotency-Key": "events-cancelled-1"},
    )
    assert cancelled_create.status_code == 201
    cancelled_id = cancelled_create.json()["transfer_id"]
    gateway_cancel = gateway_client.post(f"/v1/transfers/{cancelled_id}/cancel")
    assert gateway_cancel.status_code == 200

    # Patch gateway events passthrough to forward in-process
    events_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/events"
    )
    gateway_internal_client = events_route.endpoint.__globals__["_client"]

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.list_transfer_events = _events_inproc

    settled_events_resp = gateway_client.get(
        f"/v1/transfers/{settled_id}/events",
        headers={"X-Request-Id": "gw-events-settled-1"},
    )
    assert settled_events_resp.status_code == 200
    settled_events = settled_events_resp.json()
    settled_types = [e["event_type"] for e in settled_events]
    assert "TRANSFER_CREATED" in settled_types
    assert "TRANSFER_CONNECTOR_CALLBACK_CONFIRMED" in settled_types
    assert any(e.get("to_status") == "SETTLED" for e in settled_events)
    assert settled_events_resp.headers.get("X-Request-Id") == "gw-events-settled-1"

    cancelled_events_resp = gateway_client.get(f"/v1/transfers/{cancelled_id}/events")
    assert cancelled_events_resp.status_code == 200
    cancelled_events = cancelled_events_resp.json()
    cancelled_types = [e["event_type"] for e in cancelled_events]
    assert "TRANSFER_CREATED" in cancelled_types
    assert "TRANSFER_CANCELLED" in cancelled_types
    assert any(e.get("failure_reason") == "CANCELLED" for e in cancelled_events)


def test_gateway_transfer_events_pagination_contract(gateway_client, orchestrator_client) -> None:
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-events-page",
            "recipient_phone_e164": "+15550707072",
            "currency": "USD",
            "amount_minor": 333,
        },
        headers={"Idempotency-Key": "events-page-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    external_ref = submitted.json()["connector_external_ref"]
    orchestrator_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )

    events_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/events"
    )
    gateway_internal_client = events_route.endpoint.__globals__["_client"]

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params=params,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json(), headers=dict(resp.headers))

    gateway_internal_client.list_transfer_events = _events_inproc

    full = gateway_client.get(f"/v1/transfers/{transfer_id}/events")
    assert full.status_code == 200
    full_events = full.json()
    assert len(full_events) >= 5

    page1 = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        params={"limit": 2},
    )
    assert page1.status_code == 200
    p1_events = page1.json()
    cursor1 = page1.headers.get("X-Next-Cursor")
    assert len(p1_events) == 2
    assert cursor1

    page2 = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        params={"limit": 2, "cursor": cursor1},
    )
    assert page2.status_code == 200
    p2_events = page2.json()
    assert len(p2_events) >= 2

    combined = p1_events + p2_events
    combined_ids = [e["event_id"] for e in combined]
    assert len(set(combined_ids)) == len(combined_ids)
    assert combined_ids == [e["event_id"] for e in full_events[: len(combined_ids)]]


def test_gateway_connector_transaction_events_passthrough_contract(gateway_client, connector_client) -> None:
    # Create two connector transactions and only confirm one of them.
    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-feed-1",
            "external_ref": "conn-feed-ref-1",
            "amount_minor": 501,
            "currency": "USD",
            "destination": "acct-conn-1",
        },
    )
    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-feed-2",
            "external_ref": "conn-feed-ref-2",
            "amount_minor": 502,
            "currency": "USD",
            "destination": "acct-conn-2",
        },
    )
    connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "conn-feed-ref-1", "status": "CONFIRMED"},
    )

    # Patch gateway connector-events passthrough to forward in-process.
    conn_events_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transaction-events"
    )
    gateway_globals = conn_events_route.endpoint.__globals__
    gateway_connector_client = gateway_globals["_connector_client"]

    async def _conn_events_inproc(params: dict, headers: dict) -> Any:
        resp = connector_client.get(
            "/v1/connectors/transaction-events",
            params=params,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_connector_client.list_transaction_events = _conn_events_inproc

    # Filter by external_ref should return only events for that reference.
    by_ref = gateway_client.get(
        "/v1/connectors/transaction-events",
        params={"external_ref": "conn-feed-ref-1"},
        headers={"X-Request-Id": "conn-feed-req-1"},
    )
    assert by_ref.status_code == 200
    by_ref_rows = by_ref.json()
    assert len(by_ref_rows) >= 2
    assert all(row["external_ref"] == "conn-feed-ref-1" for row in by_ref_rows)
    assert by_ref.headers.get("X-Request-Id") == "conn-feed-req-1"

    # Filter by status should only return matching status rows.
    by_status = gateway_client.get(
        "/v1/connectors/transaction-events",
        params={"status": "CONFIRMED"},
    )
    assert by_status.status_code == 200
    by_status_rows = by_status.json()
    assert len(by_status_rows) >= 1
    assert all(row["status"] == "CONFIRMED" for row in by_status_rows)
    assert any(row["external_ref"] == "conn-feed-ref-1" for row in by_status_rows)

    # Reconciliation service-mode reader expectation: latest event per external_ref is current state.
    all_rows_resp = gateway_client.get("/v1/connectors/transaction-events")
    assert all_rows_resp.status_code == 200
    latest_by_ref = {}
    for row in all_rows_resp.json():
        latest_by_ref[row["external_ref"]] = row

    assert latest_by_ref["conn-feed-ref-1"]["status"] == "CONFIRMED"
    assert latest_by_ref["conn-feed-ref-2"]["status"] == "PENDING"


def test_gateway_connector_transaction_lookup_status_progression_contract(
    gateway_client, connector_client
) -> None:
    external_ref = "conn-lookup-ref-1"

    create = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-lookup-1",
            "external_ref": external_ref,
            "amount_minor": 333,
            "currency": "USD",
            "destination": "acct-lookup-1",
        },
    )
    assert create.status_code == 201

    lookup_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transactions/{external_ref}"
    )
    gateway_connector_client = lookup_route.endpoint.__globals__["_connector_client"]

    async def _txn_inproc(external_ref: str, headers: dict) -> Any:
        resp = connector_client.get(
            f"/v1/connectors/transactions/{external_ref}",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_connector_client.get_transaction = _txn_inproc

    before_callback = gateway_client.get(
        f"/v1/connectors/transactions/{external_ref}",
        headers={"X-Request-Id": "conn-lookup-req-1"},
    )
    assert before_callback.status_code == 200
    assert before_callback.json()["status"] == "PENDING"
    assert before_callback.headers.get("X-Request-Id") == "conn-lookup-req-1"

    callback = connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert callback.status_code == 200
    assert callback.json()["accepted"] is True

    after_callback = gateway_client.get(f"/v1/connectors/transactions/{external_ref}")
    assert after_callback.status_code == 200
    assert after_callback.json()["status"] == "CONFIRMED"


def test_gateway_connector_transactions_list_passthrough_contract(
    gateway_client, connector_client
) -> None:
    # Seed two transactions; confirm only one to create diverging latest statuses.
    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-list-1",
            "external_ref": "conn-list-ref-1",
            "amount_minor": 901,
            "currency": "USD",
            "destination": "acct-list-1",
        },
    )
    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-list-2",
            "external_ref": "conn-list-ref-2",
            "amount_minor": 902,
            "currency": "USD",
            "destination": "acct-list-2",
        },
    )
    connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "conn-list-ref-1", "status": "CONFIRMED"},
    )

    # Patch gateway transactions list passthrough in-process.
    list_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transactions"
    )
    gateway_connector_client = list_route.endpoint.__globals__["_connector_client"]

    async def _list_txn_inproc(headers: dict) -> Any:
        resp = connector_client.get("/v1/connectors/transactions", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_connector_client.list_transactions = _list_txn_inproc

    # Also patch events passthrough so we can compare list status vs latest event status.
    events_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transaction-events"
    )
    events_connector_client = events_route.endpoint.__globals__["_connector_client"]

    async def _list_events_inproc(params: dict, headers: dict) -> Any:
        resp = connector_client.get("/v1/connectors/transaction-events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    events_connector_client.list_transaction_events = _list_events_inproc

    txns_resp = gateway_client.get(
        "/v1/connectors/transactions",
        headers={"X-Request-Id": "conn-list-req-1"},
    )
    assert txns_resp.status_code == 200
    assert txns_resp.headers.get("X-Request-Id") == "conn-list-req-1"
    txns = txns_resp.json()
    status_by_ref = {row["external_ref"]: row["status"] for row in txns}

    assert status_by_ref["conn-list-ref-1"] == "CONFIRMED"
    assert status_by_ref["conn-list-ref-2"] == "PENDING"

    events_resp = gateway_client.get("/v1/connectors/transaction-events")
    assert events_resp.status_code == 200
    latest_event_by_ref = {}
    for row in events_resp.json():
        latest_event_by_ref[row["external_ref"]] = row["status"]

    # Connector list should be consistent with latest state derived from events feed.
    assert status_by_ref["conn-list-ref-1"] == latest_event_by_ref["conn-list-ref-1"]
    assert status_by_ref["conn-list-ref-2"] == latest_event_by_ref["conn-list-ref-2"]


def test_gateway_simulate_callback_passthrough_contract(
    gateway_client, connector_client
) -> None:
    """Gateway simulate-callback passthrough drives PENDING→CONFIRMED,
    observable via both gateway transaction lookup and transaction-events."""
    external_ref = "conn-sim-ref-1"

    create = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-conn-sim-1",
            "external_ref": external_ref,
            "amount_minor": 500,
            "currency": "USD",
            "destination": "acct-sim-1",
        },
    )
    assert create.status_code == 201

    # Patch gateway simulate-callback passthrough in-process.
    sim_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/simulate-callback"
    )
    gateway_connector_client = sim_route.endpoint.__globals__["_connector_client"]

    async def _sim_inproc(payload: dict, headers: dict) -> Any:
        resp = connector_client.post(
            "/v1/connectors/simulate-callback",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_connector_client.simulate_callback = _sim_inproc

    # Also patch lookup passthrough in-process.
    lookup_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transactions/{external_ref}"
    )
    lookup_connector_client = lookup_route.endpoint.__globals__["_connector_client"]

    async def _txn_inproc(external_ref: str, headers: dict) -> Any:
        resp = connector_client.get(
            f"/v1/connectors/transactions/{external_ref}",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    lookup_connector_client.get_transaction = _txn_inproc

    # Also patch events passthrough in-process.
    events_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/transaction-events"
    )
    events_connector_client = events_route.endpoint.__globals__["_connector_client"]

    async def _events_inproc(params: dict, headers: dict) -> Any:
        resp = connector_client.get(
            "/v1/connectors/transaction-events",
            params=params,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    events_connector_client.list_transaction_events = _events_inproc

    # Verify PENDING before callback.
    before = gateway_client.get(f"/v1/connectors/transactions/{external_ref}")
    assert before.status_code == 200
    assert before.json()["status"] == "PENDING"

    # Fire simulate-callback via gateway.
    sim_resp = gateway_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
        headers={"X-Request-Id": "sim-cb-req-1"},
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["accepted"] is True

    # Lookup via gateway now shows CONFIRMED.
    after = gateway_client.get(f"/v1/connectors/transactions/{external_ref}")
    assert after.status_code == 200
    assert after.json()["status"] == "CONFIRMED"

    # Events feed via gateway also shows CONFIRMED as latest status for this ref.
    events_resp = gateway_client.get(
        "/v1/connectors/transaction-events",
        params={"external_ref": external_ref},
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    latest_status = events[-1]["status"]
    assert latest_status == "CONFIRMED"


def test_gateway_reconciliation_run_service_mode_contract(
    gateway_client, orchestrator_client, ledger_client, connector_client, recon_client
) -> None:
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-gw-recon-1",
            "recipient_phone_e164": "+15550505050",
            "currency": "USD",
            "amount_minor": 1500,
        },
        headers={"Idempotency-Key": "gw-recon-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    assert submitted.status_code == 200
    external_ref = submitted.json()["connector_external_ref"]

    sender_acct = _create_ledger_account(ledger_client, "u-gw-recon-sender", "USER_AVAILABLE")
    recv_acct = _create_ledger_account(ledger_client, "u-gw-recon-recv", "USER_AVAILABLE")

    ledger_posting = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": external_ref,
            "transfer_id": transfer_id,
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": sender_acct,
                    "direction": "DEBIT",
                    "amount_minor": 1500,
                    "currency": "USD",
                },
                {
                    "account_id": recv_acct,
                    "direction": "CREDIT",
                    "amount_minor": 1500,
                    "currency": "USD",
                },
            ],
        },
    )
    assert ledger_posting.status_code == 201

    connector_create = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 1500,
            "currency": "USD",
            "destination": "acct-gw-recon-1",
        },
    )
    assert connector_create.status_code == 201

    connector_callback = connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert connector_callback.status_code == 200

    run_route = next(
        r for r in recon_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs"
    )
    recon_globals = run_route.endpoint.__globals__
    ReconService = recon_globals["ReconciliationService"]
    recon_service_module = importlib.import_module(ReconService.__module__)
    recon_settings = recon_service_module.settings

    old_mode = recon_settings.source_mode
    recon_settings.source_mode = "service"

    original_ledger_reader = ReconService._read_ledger_records_from_service
    original_connector_reader = ReconService._read_connector_records_from_service

    def _ledger_reader(self):
        rows = ledger_client.get("/v1/ledger/entries").json()
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
            }
            for row in rows
        }

    def _connector_reader(self):
        rows = connector_client.get("/v1/connectors/transaction-events").json()
        latest_by_ref = {}
        for row in rows:
            latest_by_ref[row["external_ref"]] = row
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
                "status": row["status"],
                "connector_id": row["connector_id"],
            }
            for row in latest_by_ref.values()
        }

    gateway_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs"
    )
    gateway_recon_client = gateway_route.endpoint.__globals__["_reconciliation_client"]

    async def _run_recon_inproc(headers: dict) -> Any:
        resp = recon_client.post(
            "/v1/reconciliation/runs",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_recon_client.run_reconciliation = _run_recon_inproc
    ReconService._read_ledger_records_from_service = _ledger_reader
    ReconService._read_connector_records_from_service = _connector_reader

    try:
        run_resp = gateway_client.post(
            "/v1/reconciliation/runs",
            headers={"X-Request-Id": "gw-recon-run-1"},
        )
        assert run_resp.status_code == 201
        assert run_resp.headers.get("X-Request-Id") == "gw-recon-run-1"

        body = run_resp.json()
        assert body["run"]["matched_count"] >= 1
        mismatches_for_ref = [
            mismatch for mismatch in body["mismatches"] if mismatch["external_ref"] == external_ref
        ]
        assert mismatches_for_ref == []
    finally:
        recon_settings.source_mode = old_mode
        ReconService._read_ledger_records_from_service = original_ledger_reader
        ReconService._read_connector_records_from_service = original_connector_reader


def test_gateway_reconciliation_run_detail_contract(
    gateway_client, orchestrator_client, ledger_client, connector_client, recon_client
) -> None:
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-gw-recon-detail-1",
            "recipient_phone_e164": "+15550505051",
            "currency": "USD",
            "amount_minor": 1600,
        },
        headers={"Idempotency-Key": "gw-recon-detail-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    assert submitted.status_code == 200
    external_ref = submitted.json()["connector_external_ref"]

    sender_acct = _create_ledger_account(ledger_client, "u-gw-recon-detail-sender", "USER_AVAILABLE")
    recv_acct = _create_ledger_account(ledger_client, "u-gw-recon-detail-recv", "USER_AVAILABLE")

    ledger_posting = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": external_ref,
            "transfer_id": transfer_id,
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": sender_acct,
                    "direction": "DEBIT",
                    "amount_minor": 1600,
                    "currency": "USD",
                },
                {
                    "account_id": recv_acct,
                    "direction": "CREDIT",
                    "amount_minor": 1600,
                    "currency": "USD",
                },
            ],
        },
    )
    assert ledger_posting.status_code == 201

    connector_create = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 1600,
            "currency": "USD",
            "destination": "acct-gw-recon-detail-1",
        },
    )
    assert connector_create.status_code == 201

    connector_callback = connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert connector_callback.status_code == 200

    run_route = next(
        r for r in recon_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs"
    )
    recon_globals = run_route.endpoint.__globals__
    ReconService = recon_globals["ReconciliationService"]
    recon_service_module = importlib.import_module(ReconService.__module__)
    recon_settings = recon_service_module.settings

    old_mode = recon_settings.source_mode
    recon_settings.source_mode = "service"

    original_ledger_reader = ReconService._read_ledger_records_from_service
    original_connector_reader = ReconService._read_connector_records_from_service

    def _ledger_reader(self):
        rows = ledger_client.get("/v1/ledger/entries").json()
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
            }
            for row in rows
        }

    def _connector_reader(self):
        rows = connector_client.get("/v1/connectors/transaction-events").json()
        latest_by_ref = {}
        for row in rows:
            latest_by_ref[row["external_ref"]] = row
        return {
            row["external_ref"]: {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
                "status": row["status"],
                "connector_id": row["connector_id"],
            }
            for row in latest_by_ref.values()
        }

    gateway_run_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs"
    )
    gateway_recon_client = gateway_run_route.endpoint.__globals__["_reconciliation_client"]

    async def _run_recon_inproc(headers: dict) -> Any:
        resp = recon_client.post(
            "/v1/reconciliation/runs",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_detail_route = next(
        r for r in gateway_client.app.routes if getattr(r, "path", "") == "/v1/reconciliation/runs/{run_id}"
    )
    gateway_detail_client = gateway_detail_route.endpoint.__globals__["_reconciliation_client"]

    async def _get_recon_inproc(run_id: str, headers: dict) -> Any:
        resp = recon_client.get(
            f"/v1/reconciliation/runs/{run_id}",
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_recon_client.run_reconciliation = _run_recon_inproc
    gateway_detail_client.get_reconciliation_run = _get_recon_inproc
    ReconService._read_ledger_records_from_service = _ledger_reader
    ReconService._read_connector_records_from_service = _connector_reader

    try:
        create_run_resp = gateway_client.post(
            "/v1/reconciliation/runs",
            headers={"X-Request-Id": "gw-recon-detail-run-1"},
        )
        assert create_run_resp.status_code == 201
        run_id = create_run_resp.json()["run"]["run_id"]

        detail_resp = gateway_client.get(
            f"/v1/reconciliation/runs/{run_id}",
            headers={"X-Request-Id": "gw-recon-detail-get-1"},
        )
        assert detail_resp.status_code == 200
        assert detail_resp.headers.get("X-Request-Id") == "gw-recon-detail-get-1"

        create_body = create_run_resp.json()
        detail_body = detail_resp.json()
        assert detail_body["run"]["run_id"] == run_id
        assert detail_body["run"]["matched_count"] == create_body["run"]["matched_count"]
        assert detail_body["run"]["mismatch_count"] == create_body["run"]["mismatch_count"]

        create_refs = sorted(mismatch["external_ref"] for mismatch in create_body["mismatches"])
        detail_refs = sorted(mismatch["external_ref"] for mismatch in detail_body["mismatches"])
        assert detail_refs == create_refs

        mismatches_for_ref = [
            mismatch for mismatch in detail_body["mismatches"] if mismatch["external_ref"] == external_ref
        ]
        assert mismatches_for_ref == []
    finally:
        recon_settings.source_mode = old_mode
        ReconService._read_ledger_records_from_service = original_ledger_reader
        ReconService._read_connector_records_from_service = original_connector_reader


def test_gateway_transfer_transition_contract(
    gateway_client, orchestrator_client
) -> None:
    """Transfer created through gateway can be advanced through VALIDATED and
    RESERVED via the gateway transition passthrough and remains observable via
    gateway lookup and events."""
    # Patch gateway client methods in-process BEFORE making any gateway calls.
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client_ref = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_client_ref.create_transfer = _create_inproc
    gw_client_ref.transition_transfer = _transition_inproc
    gw_client_ref.get_transfer = _lookup_inproc
    gw_client_ref.list_transfer_events = _events_inproc

    # Create transfer through gateway
    create = gateway_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-gw-trans-1",
            "recipient_phone_e164": "+15550606060",
            "currency": "USD",
            "amount_minor": 800,
        },
        headers={"Idempotency-Key": "gw-trans-x-1", "X-Request-Id": "gw-trans-create-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]
    assert create.json()["status"] == "CREATED"

    # Advance to VALIDATED through gateway
    validated = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
        headers={"X-Request-Id": "gw-trans-val-1"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALIDATED"
    assert validated.headers.get("X-Request-Id") == "gw-trans-val-1"

    # Advance to RESERVED through gateway
    reserved = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "RESERVED"},
        headers={"X-Request-Id": "gw-trans-res-1"},
    )
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "RESERVED"

    # Lookup via gateway shows RESERVED
    lookup = gateway_client.get(
        f"/v1/transfers/{transfer_id}",
        headers={"X-Request-Id": "gw-trans-lookup-1"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "RESERVED"
    assert lookup.headers.get("X-Request-Id") == "gw-trans-lookup-1"

    # Events via gateway reflect full lifecycle up to RESERVED
    events_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        headers={"X-Request-Id": "gw-trans-events-1"},
    )
    assert events_resp.status_code == 200
    event_types = [e["event_type"] for e in events_resp.json()]
    assert "TRANSFER_CREATED" in event_types
    assert any(e.get("to_status") == "VALIDATED" for e in events_resp.json())
    assert any(e.get("to_status") == "RESERVED" for e in events_resp.json())


def test_gateway_full_e2e_happy_path_contract(
    gateway_client, orchestrator_client, connector_client
) -> None:
    """Full CREATED→SETTLED lifecycle driven entirely through gateway endpoints.

    Steps:
    1. Create transfer via gateway.
    2. VALIDATED via gateway transition.
    3. RESERVED via gateway transition.
    4. SUBMITTED_TO_RAIL via gateway transition (submit_payout monkeypatched).
    5. Simulate connector callback via gateway (PENDING→CONFIRMED).
    6. Gateway connector-callback to orchestrator (SUBMITTED→SETTLED).
    7. Assert final SETTLED state visible via gateway transfer lookup.
    8. Assert full event history visible via gateway transfer events.
    """
    # --- Wire all gateway client methods in-process BEFORE the first gateway call ---
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _callback_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.get_transfer = _lookup_inproc
    gw_client.list_transfer_events = _events_inproc
    gw_client.connector_callback = _callback_inproc

    # Wire connector gateway client for simulate-callback passthrough
    sim_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/connectors/simulate-callback"
    )
    gw_connector_client = sim_route.endpoint.__globals__["_connector_client"]

    async def _sim_inproc(payload: dict, headers: dict) -> Any:
        resp = connector_client.post(
            "/v1/connectors/simulate-callback",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_connector_client.simulate_callback = _sim_inproc

    # submit_payout runs in mock mode (settings.connector_submission_mode == "mock")
    # so no patching is needed; external_ref is derived after the transition response.

    # 1. Create
    create = gateway_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-e2e-1",
            "recipient_phone_e164": "+15550707070",
            "currency": "USD",
            "amount_minor": 1000,
        },
        headers={"Idempotency-Key": "e2e-happy-1", "X-Request-Id": "e2e-create-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]
    assert create.json()["status"] == "CREATED"

    # 2. VALIDATED
    validated = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
        headers={"X-Request-Id": "e2e-val-1"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALIDATED"

    # 3. RESERVED
    reserved = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "RESERVED"},
        headers={"X-Request-Id": "e2e-res-1"},
    )
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "RESERVED"

    # 4. SUBMITTED_TO_RAIL — mock submit_payout runs automatically
    submitted = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "SUBMITTED_TO_RAIL"},
        headers={"X-Request-Id": "e2e-submit-1"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED_TO_RAIL"
    external_ref = submitted.json()["connector_external_ref"]
    assert external_ref  # non-empty ref assigned by mock connector

    # Register payout in connector store so simulate-callback can find it.
    # (Mock submit_payout bypasses the real HTTP call to the connector-gateway.)
    reg = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 1000,
            "currency": "USD",
            "destination": "acct-e2e-1",
        },
    )
    assert reg.status_code == 201

    # 5. Simulate callback (PENDING→CONFIRMED) via gateway connector passthrough
    sim = gateway_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
        headers={"X-Request-Id": "e2e-sim-1"},
    )
    assert sim.status_code == 200
    assert sim.json()["accepted"] is True

    # 6. Connector callback to orchestrator (SUBMITTED→SETTLED) via gateway
    settled_resp = gateway_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
        headers={"X-Request-Id": "e2e-cb-1"},
    )
    assert settled_resp.status_code == 200
    assert settled_resp.json()["status"] == "SETTLED"
    assert settled_resp.headers.get("X-Request-Id") == "e2e-cb-1"

    # 7. Transfer lookup via gateway shows SETTLED
    lookup = gateway_client.get(
        f"/v1/transfers/{transfer_id}",
        headers={"X-Request-Id": "e2e-lookup-1"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "SETTLED"
    assert lookup.json()["connector_external_ref"] == external_ref
    assert lookup.headers.get("X-Request-Id") == "e2e-lookup-1"

    # 8. Events feed via gateway shows full lifecycle
    events_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        headers={"X-Request-Id": "e2e-events-1"},
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    event_types = [e["event_type"] for e in events]
    assert "TRANSFER_CREATED" in event_types
    assert any(e.get("to_status") == "VALIDATED" for e in events)
    assert any(e.get("to_status") == "RESERVED" for e in events)
    assert any(e.get("to_status") == "SUBMITTED_TO_RAIL" for e in events)
    assert any(e.get("to_status") == "SETTLED" for e in events)


def test_gateway_idempotency_contract(gateway_client, orchestrator_client) -> None:
    """Duplicate create-transfer requests with the same Idempotency-Key are
    short-circuited by the gateway middleware: the upstream orchestrator is
    called exactly once and both responses carry the same transfer_id."""

    # Wire gateway create-transfer in-process to orchestrator so we can count calls.
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    call_count = {"n": 0}

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        call_count["n"] += 1
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc

    payload = {
        "sender_user_id": "u-idem-gw-1",
        "recipient_phone_e164": "+15550808080",
        "currency": "USD",
        "amount_minor": 250,
    }
    idem_key = "idem-gw-contract-1"

    # First request — reaches the orchestrator.
    first = gateway_client.post(
        "/v1/transfers",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert first.status_code == 201
    transfer_id = first.json()["transfer_id"]

    # Second request with the same key+body — replayed by the gateway middleware.
    second = gateway_client.post(
        "/v1/transfers",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert second.status_code == 201
    assert second.json()["transfer_id"] == transfer_id

    # Orchestrator route was reached exactly once.
    assert call_count["n"] == 1

    # Request without an Idempotency-Key is rejected at the gateway.
    no_key = gateway_client.post("/v1/transfers", json=payload)
    assert no_key.status_code == 400
    assert "Idempotency-Key" in no_key.json()["detail"]


def test_gateway_failed_transition_contract(
    gateway_client, orchestrator_client
) -> None:
    """A transfer explicitly transitioned to FAILED via the gateway exposes
    the failure_reason on lookup and in the events feed."""

    # Wire gateway client methods in-process before any call.
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.get_transfer = _lookup_inproc
    gw_client.list_transfer_events = _events_inproc

    # 1. Create a transfer.
    create = gateway_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-fail-1",
            "recipient_phone_e164": "+15550909090",
            "currency": "USD",
            "amount_minor": 500,
        },
        headers={"Idempotency-Key": "fail-contract-1", "X-Request-Id": "fail-create-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    # 2. Advance to VALIDATED then RESERVED.
    val = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
        headers={"X-Request-Id": "fail-val-1"},
    )
    assert val.status_code == 200
    assert val.json()["status"] == "VALIDATED"

    res = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "RESERVED"},
        headers={"X-Request-Id": "fail-res-1"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESERVED"

    # 3. Fail the transfer with an explicit reason.
    failure_reason = "connector_unavailable"
    failed = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "FAILED", "failure_reason": failure_reason},
        headers={"X-Request-Id": "fail-transition-1"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert failed.json()["failure_reason"] == failure_reason

    # 4. Gateway lookup returns FAILED with the reason.
    lookup = gateway_client.get(
        f"/v1/transfers/{transfer_id}",
        headers={"X-Request-Id": "fail-lookup-1"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "FAILED"
    assert lookup.json()["failure_reason"] == failure_reason
    assert lookup.headers.get("X-Request-Id") == "fail-lookup-1"

    # 5. Further transitions from FAILED are rejected (terminal status).
    retry = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
        headers={"X-Request-Id": "fail-retry-1"},
    )
    assert retry.status_code == 409

    # 6. Events feed shows the full lifecycle ending with the FAILED event.
    events_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        headers={"X-Request-Id": "fail-events-1"},
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert any(e.get("to_status") == "VALIDATED" for e in events)
    assert any(e.get("to_status") == "RESERVED" for e in events)
    failed_events = [e for e in events if e.get("to_status") == "FAILED"]
    assert failed_events, "expected at least one FAILED event"
    assert failed_events[-1].get("failure_reason") == failure_reason


def test_gateway_reversed_transition_contract(
    gateway_client, orchestrator_client, connector_client
) -> None:
    """A SETTLED transfer transitioned to REVERSED via the gateway exposes
    REVERSED status on lookup and a reversal event with the reason in the events feed."""

    # Wire all gateway client methods in-process before the first call.
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _callback_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.get_transfer = _lookup_inproc
    gw_client.list_transfer_events = _events_inproc
    gw_client.connector_callback = _callback_inproc

    # 1. Create and advance to SETTLED (reuse mock submit_payout path).
    create = gateway_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-rev-gw-1",
            "recipient_phone_e164": "+15551010101",
            "currency": "USD",
            "amount_minor": 750,
        },
        headers={"Idempotency-Key": "rev-gw-contract-1", "X-Request-Id": "rev-create-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    for status in ("VALIDATED", "RESERVED"):
        resp = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json={"status": status},
        )
        assert resp.status_code == 200

    submitted = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "SUBMITTED_TO_RAIL"},
    )
    assert submitted.status_code == 200
    external_ref = submitted.json()["connector_external_ref"]
    assert external_ref

    # Register payout in connector store so callback can find it.
    connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 750,
            "currency": "USD",
            "destination": "acct-rev-gw-1",
        },
    )

    settled = gateway_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert settled.status_code == 200
    assert settled.json()["status"] == "SETTLED"

    # 2. Reverse the transfer via gateway with an explicit reason.
    reversal_reason = "chargeback_accepted"
    reversed_resp = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "REVERSED", "failure_reason": reversal_reason},
        headers={"X-Request-Id": "rev-transition-1"},
    )
    assert reversed_resp.status_code == 200
    assert reversed_resp.json()["status"] == "REVERSED"
    assert reversed_resp.json()["failure_reason"] == reversal_reason

    # 3. Gateway lookup shows REVERSED.
    lookup = gateway_client.get(
        f"/v1/transfers/{transfer_id}",
        headers={"X-Request-Id": "rev-lookup-1"},
    )
    assert lookup.status_code == 200
    assert lookup.json()["status"] == "REVERSED"
    assert lookup.json()["failure_reason"] == reversal_reason
    assert lookup.headers.get("X-Request-Id") == "rev-lookup-1"

    # 4. REVERSED is terminal — further transitions must be rejected.
    rejected = gateway_client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "SETTLED", "failure_reason": "re_settle"},
    )
    assert rejected.status_code == 409

    # 5. Events feed contains the REVERSED event with the reversal reason.
    events_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events",
        headers={"X-Request-Id": "rev-events-1"},
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    reversed_events = [e for e in events if e.get("to_status") == "REVERSED"]
    assert reversed_events, "expected at least one REVERSED event"
    assert reversed_events[-1]["failure_reason"] == reversal_reason
    assert any(e.get("to_status") == "SETTLED" for e in events)




def test_gateway_ledger_posting_on_submission_contract(
    gateway_client, orchestrator_client, ledger_client
) -> None:
    """After a transfer reaches SUBMITTED_TO_RAIL via the gateway, the sender's
    ledger balance reflects the debit and the transit account reflects the credit."""

    # 1. Create ledger accounts directly in the ledger service.
    sender_acct_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": "u-led-gw-1",
            "account_type": "USER_AVAILABLE",
            "currency": "USD",
        },
    )
    assert sender_acct_resp.status_code == 201
    sender_acct_id = sender_acct_resp.json()["account_id"]

    transit_acct_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": "transit-pool",
            "account_type": "CONNECTOR_SETTLEMENT",
            "currency": "USD",
        },
    )
    assert transit_acct_resp.status_code == 201
    transit_acct_id = transit_acct_resp.json()["account_id"]

    # 2. Seed the sender's balance via a treasury DEBIT → sender CREDIT adjustment.
    treasury_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": "treasury",
            "account_type": "TREASURY",
            "currency": "USD",
        },
    )
    assert treasury_resp.status_code == 201
    treasury_acct_id = treasury_resp.json()["account_id"]

    seed = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "seed-led-gw-1",
            "transfer_id": "seed-transfer-1",
            "entry_type": "ADJUSTMENT",
            "postings": [
                {"account_id": treasury_acct_id, "direction": "DEBIT", "amount_minor": 50000, "currency": "USD"},
                {"account_id": sender_acct_id, "direction": "CREDIT", "amount_minor": 50000, "currency": "USD"},
            ],
        },
    )
    assert seed.status_code == 201
    bal_before = ledger_client.get(f"/v1/ledger/accounts/{sender_acct_id}/balance")
    assert bal_before.json()["balance_minor"] == 50000

    # 3. Wire gateway → orchestrator in-process.
    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json=payload, headers=headers
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc

    # 4. Get the orchestrator's service module dict to monkeypatch.
    #    sys.modules["app.domain.service"] is unsafe — _load_service() overwrites
    #    it for each service loaded after the orchestrator.  Using the class's
    #    method __globals__ gives us the exact dict for the orchestrator service.
    orch_transition_route = next(
        r for r in orchestrator_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/transition"
    )
    orch_cls = orch_transition_route.endpoint.__globals__["PaymentOrchestratorService"]
    svc_dict = orch_cls.transition_transfer.__globals__

    def _inproc_post_entry(transfer):
        resp = ledger_client.post(
            "/v1/ledger/postings",
            json={
                "external_ref": f"payout-{transfer.transfer_id}",
                "transfer_id": transfer.transfer_id,
                "entry_type": "TRANSFER",
                "postings": [
                    {
                        "account_id": transfer.sender_ledger_account_id,
                        "direction": "DEBIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                    {
                        "account_id": transfer.transit_ledger_account_id,
                        "direction": "CREDIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        return {"ok": "true", "entry_id": resp.json()["entry_id"]}

    original_post_entry = svc_dict["post_transfer_entry"]
    original_ledger_enabled = svc_dict["settings"].ledger_posting_enabled
    svc_dict["post_transfer_entry"] = _inproc_post_entry
    svc_dict["settings"].ledger_posting_enabled = True

    try:
        # 5. Create transfer via gateway supplying the ledger account IDs.
        create = gateway_client.post(
            "/v1/transfers",
            json={
                "sender_user_id": "u-led-gw-1",
                "recipient_phone_e164": "+15551212121",
                "currency": "USD",
                "amount_minor": 1500,
                "sender_ledger_account_id": sender_acct_id,
                "transit_ledger_account_id": transit_acct_id,
            },
            headers={"Idempotency-Key": "led-gw-contract-1"},
        )
        assert create.status_code == 201
        transfer_id = create.json()["transfer_id"]
        assert create.json()["sender_ledger_account_id"] == sender_acct_id
        assert create.json()["transit_ledger_account_id"] == transit_acct_id

        # 6. Advance to SUBMITTED_TO_RAIL — ledger posting fires here.
        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
        submitted = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "SUBMITTED_TO_RAIL"

        # 7. Sender balance must be deducted by 1500.
        sender_bal = ledger_client.get(f"/v1/ledger/accounts/{sender_acct_id}/balance")
        assert sender_bal.json()["balance_minor"] == 50000 - 1500

        # 8. Transit account must be credited by 1500.
        transit_bal = ledger_client.get(f"/v1/ledger/accounts/{transit_acct_id}/balance")
        assert transit_bal.json()["balance_minor"] == 1500
    finally:
        svc_dict["post_transfer_entry"] = original_post_entry
        svc_dict["settings"].ledger_posting_enabled = original_ledger_enabled


def test_gateway_ledger_reversal_posting_on_reversed_contract(
    gateway_client, orchestrator_client, ledger_client
) -> None:
    """After a SETTLED transfer is reversed, the transit account is debited back
    and the sender account is credited back."""

    sender_acct_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": "u-led-gw-rev-1",
            "account_type": "USER_AVAILABLE",
            "currency": "USD",
        },
    )
    assert sender_acct_resp.status_code == 201
    sender_acct_id = sender_acct_resp.json()["account_id"]

    transit_acct_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": "transit-pool-rev",
            "account_type": "CONNECTOR_SETTLEMENT",
            "currency": "USD",
        },
    )
    assert transit_acct_resp.status_code == 201
    transit_acct_id = transit_acct_resp.json()["account_id"]

    treasury_resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": "treasury-rev",
            "account_type": "TREASURY",
            "currency": "USD",
        },
    )
    assert treasury_resp.status_code == 201
    treasury_acct_id = treasury_resp.json()["account_id"]

    seed = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "seed-led-gw-rev-1",
            "transfer_id": "seed-transfer-rev-1",
            "entry_type": "ADJUSTMENT",
            "postings": [
                {"account_id": treasury_acct_id, "direction": "DEBIT", "amount_minor": 50000, "currency": "USD"},
                {"account_id": sender_acct_id, "direction": "CREDIT", "amount_minor": 50000, "currency": "USD"},
            ],
        },
    )
    assert seed.status_code == 201

    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json=payload, headers=headers
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _callback_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.connector_callback = _callback_inproc

    orch_transition_route = next(
        r for r in orchestrator_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/transition"
    )
    orch_cls = orch_transition_route.endpoint.__globals__["PaymentOrchestratorService"]
    svc_dict = orch_cls.transition_transfer.__globals__

    def _inproc_post_entry(transfer):
        resp = ledger_client.post(
            "/v1/ledger/postings",
            json={
                "external_ref": f"payout-{transfer.transfer_id}",
                "transfer_id": transfer.transfer_id,
                "entry_type": "TRANSFER",
                "postings": [
                    {
                        "account_id": transfer.sender_ledger_account_id,
                        "direction": "DEBIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                    {
                        "account_id": transfer.transit_ledger_account_id,
                        "direction": "CREDIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        return {"ok": "true", "entry_id": resp.json()["entry_id"]}

    captured = {"reversal_entry_id": None}

    def _inproc_post_reversal_entry(transfer):
        resp = ledger_client.post(
            "/v1/ledger/postings",
            json={
                "external_ref": f"reversal-{transfer.transfer_id}",
                "transfer_id": transfer.transfer_id,
                "entry_type": "REVERSAL",
                "postings": [
                    {
                        "account_id": transfer.transit_ledger_account_id,
                        "direction": "DEBIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                    {
                        "account_id": transfer.sender_ledger_account_id,
                        "direction": "CREDIT",
                        "amount_minor": transfer.amount_minor,
                        "currency": transfer.currency,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        captured["reversal_entry_id"] = resp.json()["entry_id"]
        return {"ok": "true", "entry_id": resp.json()["entry_id"]}

    original_post_entry = svc_dict["post_transfer_entry"]
    original_post_reversal_entry = svc_dict["post_reversal_entry"]
    original_ledger_enabled = svc_dict["settings"].ledger_posting_enabled
    svc_dict["post_transfer_entry"] = _inproc_post_entry
    svc_dict["post_reversal_entry"] = _inproc_post_reversal_entry
    svc_dict["settings"].ledger_posting_enabled = True

    try:
        create = gateway_client.post(
            "/v1/transfers",
            json={
                "sender_user_id": "u-led-gw-rev-1",
                "recipient_phone_e164": "+15551213131",
                "currency": "USD",
                "amount_minor": 1800,
                "sender_ledger_account_id": sender_acct_id,
                "transit_ledger_account_id": transit_acct_id,
            },
            headers={"Idempotency-Key": "led-gw-rev-contract-1"},
        )
        assert create.status_code == 201
        transfer_id = create.json()["transfer_id"]

        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
        submitted = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
        )
        assert submitted.status_code == 200
        external_ref = submitted.json()["connector_external_ref"]

        settled = gateway_client.post(
            "/v1/transfers/callbacks/connector",
            json={"external_ref": external_ref, "status": "CONFIRMED"},
        )
        assert settled.status_code == 200
        assert settled.json()["status"] == "SETTLED"

        reversed_resp = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json={"status": "REVERSED", "failure_reason": "chargeback_accepted"},
        )
        assert reversed_resp.status_code == 200
        assert reversed_resp.json()["status"] == "REVERSED"

        reversal_entry = ledger_client.get(f"/v1/ledger/entries/{captured['reversal_entry_id']}")
        assert reversal_entry.status_code == 200
        assert reversal_entry.json()["entry_type"] == "REVERSAL"

        sender_bal = ledger_client.get(f"/v1/ledger/accounts/{sender_acct_id}/balance")
        assert sender_bal.json()["balance_minor"] == 50000

        transit_bal = ledger_client.get(f"/v1/ledger/accounts/{transit_acct_id}/balance")
        assert transit_bal.json()["balance_minor"] == 0
    finally:
        svc_dict["post_transfer_entry"] = original_post_entry
        svc_dict["post_reversal_entry"] = original_post_reversal_entry
        svc_dict["settings"].ledger_posting_enabled = original_ledger_enabled


def test_gateway_ledger_submission_failure_contract(
    gateway_client, orchestrator_client
) -> None:
    """If ledger posting fails on RESERVED->SUBMITTED_TO_RAIL, the transfer is
    marked FAILED and the reason is visible through gateway lookup/events."""

    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json=payload, headers=headers
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.get_transfer = _lookup_inproc
    gw_client.list_transfer_events = _events_inproc

    orch_transition_route = next(
        r for r in orchestrator_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/transition"
    )
    orch_cls = orch_transition_route.endpoint.__globals__["PaymentOrchestratorService"]
    svc_dict = orch_cls.transition_transfer.__globals__

    original_post_entry = svc_dict["post_transfer_entry"]
    original_ledger_enabled = svc_dict["settings"].ledger_posting_enabled
    svc_dict["post_transfer_entry"] = lambda _t: {"ok": "false", "reason": "ledger_unavailable"}
    svc_dict["settings"].ledger_posting_enabled = True

    try:
        create = gateway_client.post(
            "/v1/transfers",
            json={
                "sender_user_id": "u-led-sub-fail-gw-1",
                "recipient_phone_e164": "+15551214141",
                "currency": "USD",
                "amount_minor": 700,
                "sender_ledger_account_id": "acct-led-sub-fail-sender",
                "transit_ledger_account_id": "acct-led-sub-fail-transit",
            },
            headers={"Idempotency-Key": "led-sub-fail-gw-idem-1"},
        )
        assert create.status_code == 201
        transfer_id = create.json()["transfer_id"]

        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
        failed = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
        )
        assert failed.status_code == 200
        assert failed.json()["status"] == "FAILED"
        assert failed.json()["failure_reason"] == "ledger_unavailable"

        lookup = gateway_client.get(f"/v1/transfers/{transfer_id}")
        assert lookup.status_code == 200
        assert lookup.json()["status"] == "FAILED"
        assert lookup.json()["failure_reason"] == "ledger_unavailable"

        events = gateway_client.get(f"/v1/transfers/{transfer_id}/events").json()
        failed_events = [e for e in events if e.get("to_status") == "FAILED"]
        assert failed_events
        assert failed_events[-1]["failure_reason"] == "ledger_unavailable"

        filtered = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"event_type": "TRANSFER_LEDGER_POSTING_FAILED"},
        )
        assert filtered.status_code == 200
        filtered_events = filtered.json()
        assert len(filtered_events) == 1
        assert filtered_events[0]["event_type"] == "TRANSFER_LEDGER_POSTING_FAILED"
        assert filtered_events[0]["failure_reason"] == "ledger_unavailable"

        failed_only = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"to_status": "FAILED"},
        )
        assert failed_only.status_code == 200
        failed_only_events = failed_only.json()
        assert failed_only_events
        assert all(e["to_status"] == "FAILED" for e in failed_only_events)

        combined = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"event_type": "TRANSFER_LEDGER_POSTING_FAILED", "to_status": "FAILED"},
        )
        assert combined.status_code == 200
        combined_events = combined.json()
        assert len(combined_events) == 1
        assert combined_events[0]["event_type"] == "TRANSFER_LEDGER_POSTING_FAILED"
        assert combined_events[0]["to_status"] == "FAILED"
    finally:
        svc_dict["post_transfer_entry"] = original_post_entry
        svc_dict["settings"].ledger_posting_enabled = original_ledger_enabled


def test_gateway_ledger_reversal_failure_contract(
    gateway_client, orchestrator_client
) -> None:
    """If ledger reversal posting fails on SETTLED->REVERSED, transfer ends
    in FAILED and the reason is visible through gateway lookup/events."""

    gw_xfer_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and getattr(r, "methods", None) == {"POST"}
    )
    gw_client = gw_xfer_route.endpoint.__globals__["_client"]

    async def _create_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post("/v1/transfers", json=payload, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _transition_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json=payload, headers=headers
        )
        return _DummyResponse(resp.status_code, resp.json())

    async def _lookup_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    async def _callback_inproc(payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.create_transfer = _create_inproc
    gw_client.transition_transfer = _transition_inproc
    gw_client.get_transfer = _lookup_inproc
    gw_client.list_transfer_events = _events_inproc
    gw_client.connector_callback = _callback_inproc

    orch_transition_route = next(
        r for r in orchestrator_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/transition"
    )
    orch_cls = orch_transition_route.endpoint.__globals__["PaymentOrchestratorService"]
    svc_dict = orch_cls.transition_transfer.__globals__

    original_post_entry = svc_dict["post_transfer_entry"]
    original_post_reversal_entry = svc_dict["post_reversal_entry"]
    original_ledger_enabled = svc_dict["settings"].ledger_posting_enabled
    svc_dict["post_transfer_entry"] = lambda _t: {"ok": "true", "entry_id": "submission-ok"}
    svc_dict["post_reversal_entry"] = lambda _t: {"ok": "false", "reason": "ledger_reversal_unavailable"}
    svc_dict["settings"].ledger_posting_enabled = True

    try:
        create = gateway_client.post(
            "/v1/transfers",
            json={
                "sender_user_id": "u-led-rev-fail-gw-1",
                "recipient_phone_e164": "+15551215151",
                "currency": "USD",
                "amount_minor": 900,
                "sender_ledger_account_id": "acct-led-rev-fail-sender",
                "transit_ledger_account_id": "acct-led-rev-fail-transit",
            },
            headers={"Idempotency-Key": "led-rev-fail-gw-idem-1"},
        )
        assert create.status_code == 201
        transfer_id = create.json()["transfer_id"]

        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
        gateway_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
        submitted = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
        )
        assert submitted.status_code == 200
        external_ref = submitted.json()["connector_external_ref"]

        settled = gateway_client.post(
            "/v1/transfers/callbacks/connector",
            json={"external_ref": external_ref, "status": "CONFIRMED"},
        )
        assert settled.status_code == 200
        assert settled.json()["status"] == "SETTLED"

        failed = gateway_client.post(
            f"/v1/transfers/{transfer_id}/transition",
            json={"status": "REVERSED", "failure_reason": "chargeback_request"},
        )
        assert failed.status_code == 200
        assert failed.json()["status"] == "FAILED"
        assert failed.json()["failure_reason"] == "ledger_reversal_unavailable"

        lookup = gateway_client.get(f"/v1/transfers/{transfer_id}")
        assert lookup.status_code == 200
        assert lookup.json()["status"] == "FAILED"
        assert lookup.json()["failure_reason"] == "ledger_reversal_unavailable"

        events = gateway_client.get(f"/v1/transfers/{transfer_id}/events").json()
        failed_events = [e for e in events if e.get("to_status") == "FAILED"]
        assert failed_events
        assert failed_events[-1]["failure_reason"] == "ledger_reversal_unavailable"

        filtered = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"event_type": "TRANSFER_LEDGER_REVERSAL_POSTING_FAILED"},
        )
        assert filtered.status_code == 200
        filtered_events = filtered.json()
        assert len(filtered_events) == 1
        assert filtered_events[0]["event_type"] == "TRANSFER_LEDGER_REVERSAL_POSTING_FAILED"
        assert filtered_events[0]["failure_reason"] == "ledger_reversal_unavailable"

        failed_only = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"to_status": "FAILED"},
        )
        assert failed_only.status_code == 200
        failed_only_events = failed_only.json()
        assert failed_only_events
        assert all(e["to_status"] == "FAILED" for e in failed_only_events)

        combined = gateway_client.get(
            f"/v1/transfers/{transfer_id}/events",
            params={"event_type": "TRANSFER_LEDGER_REVERSAL_POSTING_FAILED", "to_status": "FAILED"},
        )
        assert combined.status_code == 200
        combined_events = combined.json()
        assert len(combined_events) == 1
        assert combined_events[0]["event_type"] == "TRANSFER_LEDGER_REVERSAL_POSTING_FAILED"
        assert combined_events[0]["to_status"] == "FAILED"
    finally:
        svc_dict["post_transfer_entry"] = original_post_entry
        svc_dict["post_reversal_entry"] = original_post_reversal_entry
        svc_dict["settings"].ledger_posting_enabled = original_ledger_enabled


def test_gateway_transfer_events_invalid_to_status_contract(gateway_client) -> None:
    resp = gateway_client.get(
        "/v1/transfers/t-invalid/events",
        params={"to_status": "NOT_A_STATUS"},
    )

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail[0]["loc"] == ["query", "to_status"]


def test_gateway_transfer_events_summary_contract(gateway_client, orchestrator_client) -> None:
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-events-summary",
            "recipient_phone_e164": "+15551216161",
            "currency": "USD",
            "amount_minor": 410,
        },
        headers={"Idempotency-Key": "events-summary-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    external_ref = submitted.json()["connector_external_ref"]
    orchestrator_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )

    events_summary_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/events/summary"
    )
    gateway_internal_client = events_summary_route.endpoint.__globals__["_client"]

    async def _summary_inproc(transfer_id: str, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events/summary", headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.get_transfer_event_summary = _summary_inproc

    summary_resp = gateway_client.get(
        f"/v1/transfers/{transfer_id}/events/summary",
        headers={"X-Request-Id": "gw-events-summary-1"},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["transfer_id"] == transfer_id
    assert summary["total_events"] >= 5
    assert summary["by_event_type"].get("TRANSFER_CREATED") == 1
    assert summary["by_to_status"].get("SETTLED") == 1
    assert summary_resp.headers.get("X-Request-Id") == "gw-events-summary-1"


def test_gateway_transfer_date_range_filter_contract(gateway_client, orchestrator_client) -> None:
    """Date-range filters work end-to-end through gateway → orchestrator."""
    from datetime import datetime, timedelta, timezone

    before = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()

    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-contr-date",
            "recipient_phone_e164": "+15559990001",
            "currency": "USD",
            "amount_minor": 750,
        },
        headers={"Idempotency-Key": "contr-date-range-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    after = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    far_future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

    # Patch list_transfers in-process
    list_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and "GET" in getattr(r, "methods", set())
    )
    gw_client = list_route.endpoint.__globals__["_client"]

    async def _list_inproc(params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get("/v1/transfers", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_client.list_transfers = _list_inproc

    # Transfer in range → count == 1
    resp_in = gateway_client.get("/v1/transfers", params={
        "sender_user_id": "u-contr-date",
        "created_at_from": before,
        "created_at_to": after,
    })
    assert resp_in.status_code == 200
    assert resp_in.json()["count"] == 1

    # Transfer before range → count == 0
    resp_out = gateway_client.get("/v1/transfers", params={
        "sender_user_id": "u-contr-date",
        "created_at_from": after,
        "created_at_to": far_future,
    })
    assert resp_out.status_code == 200
    assert resp_out.json()["count"] == 0

    # Patch list_transfer_events in-process
    events_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/events"
    )
    gw_events_client = events_route.endpoint.__globals__["_client"]

    async def _events_inproc(transfer_id: str, params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gw_events_client.list_transfer_events = _events_inproc

    # Events in range → at least 1
    resp_events_in = gateway_client.get(f"/v1/transfers/{transfer_id}/events", params={
        "created_at_from": before,
        "created_at_to": after,
    })
    assert resp_events_in.status_code == 200
    assert len(resp_events_in.json()) >= 1

    # Events out of range → empty list
    resp_events_out = gateway_client.get(f"/v1/transfers/{transfer_id}/events", params={
        "created_at_from": after,
        "created_at_to": far_future,
    })
    assert resp_events_out.status_code == 200
    assert resp_events_out.json() == []


def test_gateway_transfer_note_update_contract(gateway_client, orchestrator_client) -> None:
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-note-contract",
            "recipient_phone_e164": "+15558880001",
            "currency": "USD",
            "amount_minor": 610,
            "note": "initial",
        },
        headers={"Idempotency-Key": "note-contract-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    note_route = next(
        r
        for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers/{transfer_id}/note"
    )
    gateway_internal_client = note_route.endpoint.__globals__["_client"]

    async def _note_inproc(transfer_id: str, payload: dict, headers: dict) -> Any:
        resp = orchestrator_client.patch(
            f"/v1/transfers/{transfer_id}/note",
            json=payload,
            headers=headers,
        )
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.update_transfer_note = _note_inproc

    update_resp = gateway_client.patch(
        f"/v1/transfers/{transfer_id}/note",
        json={"note": "support follow-up"},
        headers={"X-Request-Id": "gw-note-1"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["note"] == "support follow-up"
    assert update_resp.headers.get("X-Request-Id") == "gw-note-1"

    lookup_resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}")
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["note"] == "support follow-up"


def test_gateway_transfer_search_contract(gateway_client, orchestrator_client) -> None:
    note_transfer = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-search-contract",
            "recipient_phone_e164": "+15557771111",
            "currency": "USD",
            "amount_minor": 210,
            "note": "Dinner reimbursement",
        },
        headers={"Idempotency-Key": "search-contract-note-1"},
    )
    assert note_transfer.status_code == 201

    failed_transfer = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-search-contract",
            "recipient_phone_e164": "+15557771112",
            "currency": "USD",
            "amount_minor": 220,
        },
        headers={"Idempotency-Key": "search-contract-fail-1"},
    )
    assert failed_transfer.status_code == 201
    failed_id = failed_transfer.json()["transfer_id"]

    failed_update = orchestrator_client.post(
        f"/v1/transfers/{failed_id}/transition",
        json={"status": "FAILED", "failure_reason": "connector timeout"},
    )
    assert failed_update.status_code == 200

    list_route = next(
        r for r in gateway_client.app.routes
        if getattr(r, "path", "") == "/v1/transfers" and "GET" in getattr(r, "methods", set())
    )
    gateway_internal_client = list_route.endpoint.__globals__["_client"]

    async def _list_inproc(params: dict, headers: dict) -> Any:
        resp = orchestrator_client.get("/v1/transfers", params=params, headers=headers)
        return _DummyResponse(resp.status_code, resp.json())

    gateway_internal_client.list_transfers = _list_inproc

    note_resp = gateway_client.get("/v1/transfers", params={"sender_user_id": "u-search-contract", "q": "dinner"})
    assert note_resp.status_code == 200
    assert note_resp.json()["count"] == 1
    assert note_resp.json()["transfers"][0]["note"] == "Dinner reimbursement"

    failure_resp = gateway_client.get("/v1/transfers", params={"sender_user_id": "u-search-contract", "q": "timeout"})
    assert failure_resp.status_code == 200
    assert failure_resp.json()["count"] == 1
    assert failure_resp.json()["transfers"][0]["failure_reason"] == "connector timeout"
