import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_transfer_is_idempotent() -> None:
    payload = {
        "sender_user_id": "u-1",
        "recipient_phone_e164": "+15550009999",
        "currency": "USD",
        "amount_minor": 1200,
        "note": "rent",
    }

    first = client.post("/v1/transfers", json=payload, headers={"Idempotency-Key": "transfer-1"})
    second = client.post("/v1/transfers", json=payload, headers={"Idempotency-Key": "transfer-1"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["transfer_id"] == second.json()["transfer_id"]
    assert first.json()["status"] == "CREATED"


def test_transfer_transition_flow() -> None:
    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-2",
            "recipient_phone_e164": "+15550008888",
            "currency": "USD",
            "amount_minor": 500,
        },
        headers={"Idempotency-Key": "transfer-2"},
    )
    assert create_resp.status_code == 201
    transfer_id = create_resp.json()["transfer_id"]

    validated = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALIDATED"

    reserved = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "RESERVED"},
    )
    assert reserved.status_code == 200
    assert reserved.json()["status"] == "RESERVED"

    invalid = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "CREATED"},
    )
    assert invalid.status_code == 409


def test_created_to_validated_runs_prechecks_and_can_auto_fail() -> None:
    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-risk",
            "recipient_phone_e164": "+15550007777",
            "currency": "USD",
            "amount_minor": 200001,
            "note": "normal",
        },
        headers={"Idempotency-Key": "transfer-risk-1"},
    )
    assert create_resp.status_code == 201
    transfer_id = create_resp.json()["transfer_id"]

    validated = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "FAILED"
    assert "risk_precheck_failed" in validated.json()["failure_reason"]


def test_created_to_validated_passes_prechecks_when_rules_allow() -> None:
    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-ok",
            "recipient_phone_e164": "+15550006666",
            "currency": "USD",
            "amount_minor": 999,
            "note": "groceries",
        },
        headers={"Idempotency-Key": "transfer-precheck-pass-1"},
    )
    assert create_resp.status_code == 201
    transfer_id = create_resp.json()["transfer_id"]

    validated = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "VALIDATED"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALIDATED"
    assert validated.json()["failure_reason"] is None


def test_reserved_to_submitted_calls_connector_and_can_fail(monkeypatch) -> None:
    from app.domain import service as svc_module

    def _fake_submit_payout(_transfer):
        return {"ok": "false", "reason": "connector_status_failed"}

    monkeypatch.setattr(svc_module, "submit_payout", _fake_submit_payout)

    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-connector-fail",
            "recipient_phone_e164": "+15550004444",
            "currency": "USD",
            "amount_minor": 900,
        },
        headers={"Idempotency-Key": "transfer-connector-fail-1"},
    )
    transfer_id = create_resp.json()["transfer_id"]

    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})

    submitted = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "SUBMITTED_TO_RAIL"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "FAILED"
    assert submitted.json()["failure_reason"] == "connector_status_failed"


def test_reserved_to_submitted_calls_connector_and_succeeds(monkeypatch) -> None:
    from app.domain import service as svc_module

    def _fake_submit_payout(_transfer):
        return {"ok": "true", "reason": ""}

    monkeypatch.setattr(svc_module, "submit_payout", _fake_submit_payout)

    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-connector-ok",
            "recipient_phone_e164": "+15550003333",
            "currency": "USD",
            "amount_minor": 900,
        },
        headers={"Idempotency-Key": "transfer-connector-ok-1"},
    )
    transfer_id = create_resp.json()["transfer_id"]

    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})

    submitted = client.post(
        f"/v1/transfers/{transfer_id}/transition",
        json={"status": "SUBMITTED_TO_RAIL"},
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED_TO_RAIL"
    assert submitted.json()["failure_reason"] is None


def test_connector_callback_confirmed_sets_transfer_to_settled(monkeypatch) -> None:
    from app.domain import service as svc_module

    def _fake_submit_payout(_transfer):
        return {"ok": "true", "reason": "", "external_ref": "orchestrator-cb-1"}

    monkeypatch.setattr(svc_module, "submit_payout", _fake_submit_payout)

    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-cb-ok",
            "recipient_phone_e164": "+15550002222",
            "currency": "USD",
            "amount_minor": 555,
        },
        headers={"Idempotency-Key": "transfer-cb-ok-1"},
    )
    transfer_id = create_resp.json()["transfer_id"]

    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"})

    callback = client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": "orchestrator-cb-1", "status": "CONFIRMED"},
    )
    assert callback.status_code == 200
    assert callback.json()["status"] == "SETTLED"


def test_connector_callback_failed_sets_transfer_to_failed(monkeypatch) -> None:
    from app.domain import service as svc_module

    def _fake_submit_payout(_transfer):
        return {"ok": "true", "reason": "", "external_ref": "orchestrator-cb-2"}

    monkeypatch.setattr(svc_module, "submit_payout", _fake_submit_payout)

    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-cb-fail",
            "recipient_phone_e164": "+15550001112",
            "currency": "USD",
            "amount_minor": 556,
        },
        headers={"Idempotency-Key": "transfer-cb-fail-1"},
    )
    transfer_id = create_resp.json()["transfer_id"]

    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"})

    callback = client.post(
        "/v1/transfers/callbacks/connector",
        json={
            "external_ref": "orchestrator-cb-2",
            "status": "FAILED",
            "failure_reason": "bank_timeout",
        },
    )
    assert callback.status_code == 200
    assert callback.json()["status"] == "FAILED"
    assert callback.json()["failure_reason"] == "bank_timeout"


def test_transfer_events_record_lifecycle(monkeypatch) -> None:
    from app.domain import service as svc_module

    def _fake_submit_payout(_transfer):
        return {"ok": "true", "reason": "", "external_ref": "orchestrator-evt-1"}

    monkeypatch.setattr(svc_module, "submit_payout", _fake_submit_payout)

    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-evt",
            "recipient_phone_e164": "+15550009991",
            "currency": "USD",
            "amount_minor": 333,
        },
        headers={"Idempotency-Key": "transfer-evt-1"},
    )
    transfer_id = create_resp.json()["transfer_id"]

    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"})
    client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": "orchestrator-evt-1", "status": "CONFIRMED"},
    )

    events_resp = client.get(f"/v1/transfers/{transfer_id}/events")
    assert events_resp.status_code == 200
    event_types = [item["event_type"] for item in events_resp.json()]
    assert "TRANSFER_CREATED" in event_types
    assert "TRANSFER_STATUS_TRANSITIONED" in event_types
    assert "TRANSFER_CONNECTOR_CALLBACK_CONFIRMED" in event_types

    assert any(item["to_status"] == "SETTLED" for item in events_resp.json())


def test_transfer_list_filtering_and_pagination() -> None:
    # Create 3 transfers: 2 for sender-a, 1 for sender-b
    for i, (sender, phone) in enumerate(
        [("list-user-a", "+15551110001"), ("list-user-a", "+15551110002"), ("list-user-b", "+15551110003")],
        start=1,
    ):
        resp = client.post(
            "/v1/transfers",
            json={"sender_user_id": sender, "recipient_phone_e164": phone, "currency": "USD", "amount_minor": 100 + i},
            headers={"Idempotency-Key": f"list-idem-{i}"},
        )
        assert resp.status_code == 201

    # Filter by sender_user_id
    resp = client.get("/v1/transfers", params={"sender_user_id": "list-user-a"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert all(t["sender_user_id"] == "list-user-a" for t in data["transfers"])
    assert data["next_cursor"] is None

    # Filter by status=CREATED should return all 3
    resp_all = client.get("/v1/transfers", params={"status": "CREATED"})
    assert resp_all.json()["count"] == 3

    # Pagination: limit=1 should page through results
    page1 = client.get("/v1/transfers", params={"limit": "1"})
    assert page1.status_code == 200
    p1 = page1.json()
    assert p1["count"] == 1
    assert p1["next_cursor"] is not None

    page2 = client.get("/v1/transfers", params={"limit": "1", "cursor": p1["next_cursor"]})
    assert page2.status_code == 200
    p2 = page2.json()
    assert p2["count"] == 1
    assert p1["transfers"][0]["transfer_id"] != p2["transfers"][0]["transfer_id"]

    page3 = client.get("/v1/transfers", params={"limit": "1", "cursor": p2["next_cursor"]})
    assert page3.status_code == 200
    p3 = page3.json()
    assert p3["count"] == 1
    assert p3["next_cursor"] is None  # 3rd page exhausts all 3 records


def test_event_relay_exports_unprocessed_once_only() -> None:
    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-relay",
            "recipient_phone_e164": "+15550009990",
            "currency": "USD",
            "amount_minor": 200,
        },
        headers={"Idempotency-Key": "transfer-relay-1"},
    )
    assert create_resp.status_code == 201

    first_relay = client.post("/v1/transfers/events/relay")
    assert first_relay.status_code == 200
    assert first_relay.json()["exported_count"] >= 1

    second_relay = client.post("/v1/transfers/events/relay")
    assert second_relay.status_code == 200
    assert second_relay.json()["exported_count"] == 0
    assert second_relay.json()["events"] == []


def test_cancel_transfer_transitions_to_failed() -> None:
    create_resp = client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-cancel",
            "recipient_phone_e164": "+15551230001",
            "currency": "USD",
            "amount_minor": 999,
        },
        headers={"Idempotency-Key": "cancel-idem-1"},
    )
    assert create_resp.status_code == 201
    transfer_id = create_resp.json()["transfer_id"]

    # Cancel from CREATED
    cancel_resp = client.post(f"/v1/transfers/{transfer_id}/cancel")
    assert cancel_resp.status_code == 200
    body = cancel_resp.json()
    assert body["status"] == "FAILED"
    assert body["failure_reason"] == "CANCELLED"

    # Status is now FAILED — cancelling again must return 409
    retry = client.post(f"/v1/transfers/{transfer_id}/cancel")
    assert retry.status_code == 409


def test_cancel_transfer_allowed_from_validated_and_reserved() -> None:
    # VALIDATED
    r = client.post(
        "/v1/transfers",
        json={"sender_user_id": "u-cancel2", "recipient_phone_e164": "+15551230002", "currency": "USD", "amount_minor": 100},
        headers={"Idempotency-Key": "cancel-idem-2"},
    )
    tid = r.json()["transfer_id"]
    client.post(f"/v1/transfers/{tid}/transition", json={"status": "VALIDATED"})
    resp = client.post(f"/v1/transfers/{tid}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"
    assert resp.json()["failure_reason"] == "CANCELLED"

    # RESERVED
    r2 = client.post(
        "/v1/transfers",
        json={"sender_user_id": "u-cancel3", "recipient_phone_e164": "+15551230003", "currency": "USD", "amount_minor": 100},
        headers={"Idempotency-Key": "cancel-idem-3"},
    )
    tid2 = r2.json()["transfer_id"]
    client.post(f"/v1/transfers/{tid2}/transition", json={"status": "VALIDATED"})
    client.post(f"/v1/transfers/{tid2}/transition", json={"status": "RESERVED"})
    resp2 = client.post(f"/v1/transfers/{tid2}/cancel")
    assert resp2.status_code == 200
    assert resp2.json()["failure_reason"] == "CANCELLED"


def test_cancel_transfer_not_found_returns_404() -> None:
    resp = client.post("/v1/transfers/nonexistent-id/cancel")
    assert resp.status_code == 404
