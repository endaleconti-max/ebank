from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_transfer_requires_idempotency_key() -> None:
    resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-1",
            "recipient_phone_e164": "+15550001111",
            "currency": "USD",
            "amount_minor": 100,
        },
    )
    assert resp.status_code == 400
    assert "Idempotency-Key" in resp.json()["detail"]


def test_request_id_propagates_to_response() -> None:
    resp = client.get("/v1/healthz", headers={"X-Request-Id": "req-123"})
    assert resp.status_code == 204
    assert resp.headers.get("X-Request-Id") == "req-123"


def test_idempotency_replays_successful_create(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_create_transfer(payload: dict, headers: dict):
        calls["count"] += 1
        return DummyResponse(
            201,
            {
                "transfer_id": "t-1",
                "status": "CREATED",
                "idempotency_key": headers.get("Idempotency-Key"),
            },
        )

    monkeypatch.setattr(routes._client, "create_transfer", fake_create_transfer)

    payload = {
        "sender_user_id": "u-1",
        "recipient_phone_e164": "+15550001111",
        "currency": "USD",
        "amount_minor": 100,
    }
    headers = {"Idempotency-Key": "idem-001"}

    first = client.post("/v1/transfers", json=payload, headers=headers)
    second = client.post("/v1/transfers", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["transfer_id"] == second.json()["transfer_id"]
    assert calls["count"] == 1


def test_connector_callback_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "payload": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_connector_callback(payload: dict, headers: dict):
        calls["count"] += 1
        calls["payload"] = payload
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            {
                "transfer_id": "t-1",
                "status": "SETTLED",
                "connector_external_ref": payload.get("external_ref"),
            },
        )

    monkeypatch.setattr(routes._client, "connector_callback", fake_connector_callback)

    resp = client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": "orchestrator-t-1", "status": "CONFIRMED"},
        headers={"X-Request-Id": "gw-cb-unit-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "SETTLED"
    assert resp.json()["connector_external_ref"] == "orchestrator-t-1"
    assert calls["count"] == 1
    assert calls["payload"] == {"external_ref": "orchestrator-t-1", "status": "CONFIRMED"}
    assert calls["request_id"] == "gw-cb-unit-1"


def test_transfer_event_relay_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "limit": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_relay_events(limit: int, headers: dict):
        calls["count"] += 1
        calls["limit"] = limit
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(200, {"events": [{"event_id": "e-1"}], "exported_count": 1})

    monkeypatch.setattr(routes._client, "relay_events", fake_relay_events)

    resp = client.post(
        "/v1/transfers/events/relay?limit=5",
        headers={"X-Request-Id": "relay-req-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["exported_count"] == 1
    assert calls["count"] == 1
    assert calls["limit"] == 5
    assert calls["request_id"] == "relay-req-1"


def test_transfer_list_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "params": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_list_transfers(params: dict, headers: dict):
        calls["count"] += 1
        calls["params"] = params
        return DummyResponse(200, {"transfers": [], "next_cursor": None, "count": 0})

    monkeypatch.setattr(routes._client, "list_transfers", fake_list_transfers)

    resp = client.get("/v1/transfers", params={"sender_user_id": "u-list-1", "status": "CREATED", "limit": "5"})

    assert resp.status_code == 200
    assert resp.json()["count"] == 0
    assert calls["count"] == 1
    assert calls["params"]["sender_user_id"] == "u-list-1"
    assert calls["params"]["status"] == "CREATED"


def test_cancel_transfer_is_forwarded(monkeypatch) -> None:
    from app.api import routes
    import json

    calls = {"count": 0, "transfer_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.content = json.dumps(payload).encode("utf-8")

    async def fake_cancel_transfer(transfer_id: str, headers: dict):
        calls["count"] += 1
        calls["transfer_id"] = transfer_id
        return DummyResponse(200, {"transfer_id": transfer_id, "status": "FAILED", "failure_reason": "CANCELLED"})

    monkeypatch.setattr(routes._client, "cancel_transfer", fake_cancel_transfer)

    resp = client.post("/v1/transfers/t-cancel-1/cancel", headers={"X-Request-Id": "cancel-req-1"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"
    assert resp.json()["failure_reason"] == "CANCELLED"
    assert calls["count"] == 1
    assert calls["transfer_id"] == "t-cancel-1"


def test_transfer_events_are_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "transfer_id": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: list):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_list_transfer_events(transfer_id: str, headers: dict):
        calls["count"] += 1
        calls["transfer_id"] = transfer_id
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            [
                {"event_id": "e-1", "event_type": "TRANSFER_CREATED", "to_status": "CREATED"},
                {"event_id": "e-2", "event_type": "TRANSFER_STATUS_TRANSITIONED", "to_status": "SETTLED"},
            ],
        )

    monkeypatch.setattr(routes._client, "list_transfer_events", fake_list_transfer_events)

    resp = client.get(
        "/v1/transfers/t-events-1/events",
        headers={"X-Request-Id": "evt-req-1"},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert calls["count"] == 1
    assert calls["transfer_id"] == "t-events-1"
    assert calls["request_id"] == "evt-req-1"


def test_connector_transaction_events_are_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "params": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: list):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_list_transaction_events(params: dict, headers: dict):
        calls["count"] += 1
        calls["params"] = params
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            [
                {"event_id": "ce-1", "external_ref": "ref-1", "status": "CONFIRMED"},
            ],
        )

    monkeypatch.setattr(routes._connector_client, "list_transaction_events", fake_list_transaction_events)

    resp = client.get(
        "/v1/connectors/transaction-events",
        params={"external_ref": "ref-1", "status": "CONFIRMED"},
        headers={"X-Request-Id": "conn-evt-req-1"},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert calls["count"] == 1
    assert calls["params"]["external_ref"] == "ref-1"
    assert calls["params"]["status"] == "CONFIRMED"
    assert calls["request_id"] == "conn-evt-req-1"


def test_connector_transaction_lookup_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "external_ref": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_get_transaction(external_ref: str, headers: dict):
        calls["count"] += 1
        calls["external_ref"] = external_ref
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            {
                "external_ref": external_ref,
                "status": "CONFIRMED",
                "connector_id": "mock-bank-a",
            },
        )

    monkeypatch.setattr(routes._connector_client, "get_transaction", fake_get_transaction)

    resp = client.get(
        "/v1/connectors/transactions/ref-lookup-1",
        headers={"X-Request-Id": "conn-txn-req-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"
    assert calls["count"] == 1
    assert calls["external_ref"] == "ref-lookup-1"
    assert calls["request_id"] == "conn-txn-req-1"


def test_connector_transactions_list_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: list):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_list_transactions(headers: dict):
        calls["count"] += 1
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            [
                {"external_ref": "ref-list-1", "status": "PENDING"},
                {"external_ref": "ref-list-2", "status": "CONFIRMED"},
            ],
        )

    monkeypatch.setattr(routes._connector_client, "list_transactions", fake_list_transactions)

    resp = client.get(
        "/v1/connectors/transactions",
        headers={"X-Request-Id": "conn-list-req-1"},
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert calls["count"] == 1
    assert calls["request_id"] == "conn-list-req-1"


def test_connector_simulate_callback_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "payload": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_simulate_callback(payload: dict, headers: dict):
        calls["count"] += 1
        calls["payload"] = payload
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(200, {"accepted": True, "transaction": {"external_ref": payload["external_ref"], "status": payload["status"]}})

    monkeypatch.setattr(routes._connector_client, "simulate_callback", fake_simulate_callback)

    resp = client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "ref-sim-1", "status": "CONFIRMED"},
        headers={"X-Request-Id": "sim-req-1"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["transaction"]["status"] == "CONFIRMED"
    assert calls["count"] == 1
    assert calls["payload"] == {"external_ref": "ref-sim-1", "status": "CONFIRMED"}
    assert calls["request_id"] == "sim-req-1"


def test_reconciliation_run_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_run_reconciliation(headers: dict):
        calls["count"] += 1
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            201,
            {
                "run": {
                    "run_id": "recon-run-1",
                    "matched_count": 1,
                    "mismatch_count": 0,
                },
                "mismatches": [],
            },
        )

    monkeypatch.setattr(routes._reconciliation_client, "run_reconciliation", fake_run_reconciliation)

    resp = client.post(
        "/v1/reconciliation/runs",
        headers={"X-Request-Id": "recon-req-1"},
    )

    assert resp.status_code == 201
    assert resp.json()["run"]["matched_count"] == 1
    assert resp.json()["mismatches"] == []
    assert calls["count"] == 1
    assert calls["request_id"] == "recon-req-1"


def test_reconciliation_run_detail_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "run_id": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json

            self.content = json.dumps(payload).encode("utf-8")

    async def fake_get_reconciliation_run(run_id: str, headers: dict):
        calls["count"] += 1
        calls["run_id"] = run_id
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(
            200,
            {
                "run": {
                    "run_id": run_id,
                    "matched_count": 2,
                    "mismatch_count": 1,
                },
                "mismatches": [
                    {"external_ref": "ref-mismatch-1", "mismatch_type": "AMOUNT_MISMATCH"},
                ],
            },
        )

    monkeypatch.setattr(routes._reconciliation_client, "get_reconciliation_run", fake_get_reconciliation_run)

    resp = client.get(
        "/v1/reconciliation/runs/recon-run-42",
        headers={"X-Request-Id": "recon-detail-req-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["run"]["run_id"] == "recon-run-42"
    assert resp.json()["run"]["matched_count"] == 2
    assert resp.json()["mismatches"][0]["mismatch_type"] == "AMOUNT_MISMATCH"
    assert calls["count"] == 1
    assert calls["run_id"] == "recon-run-42"
    assert calls["request_id"] == "recon-detail-req-1"


def test_transfer_transition_is_forwarded(monkeypatch) -> None:
    from app.api import routes

    calls = {"count": 0, "transfer_id": None, "payload": None, "request_id": None}

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            import json
            self.content = json.dumps(payload).encode("utf-8")

    async def fake_transition_transfer(transfer_id: str, payload: dict, headers: dict):
        calls["count"] += 1
        calls["transfer_id"] = transfer_id
        calls["payload"] = payload
        calls["request_id"] = headers.get("X-Request-Id")
        return DummyResponse(200, {"transfer_id": transfer_id, "status": payload.get("status")})

    monkeypatch.setattr(routes._client, "transition_transfer", fake_transition_transfer)

    resp = client.post(
        "/v1/transfers/t-trans-1/transition",
        json={"status": "VALIDATED"},
        headers={"X-Request-Id": "trans-req-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "VALIDATED"
    assert calls["count"] == 1
    assert calls["transfer_id"] == "t-trans-1"
    assert calls["payload"] == {"status": "VALIDATED"}
    assert calls["request_id"] == "trans-req-1"
