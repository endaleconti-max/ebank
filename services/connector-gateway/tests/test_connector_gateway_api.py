import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_payout_and_simulate_confirmed_callback() -> None:
    create_resp = client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-1001",
            "external_ref": "ext-cg-1001",
            "amount_minor": 1200,
            "currency": "USD",
            "destination": "acct-001",
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["status"] == "PENDING"

    simulate_resp = client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "ext-cg-1001", "status": "CONFIRMED"},
    )
    assert simulate_resp.status_code == 200
    assert simulate_resp.json()["accepted"] is True
    assert simulate_resp.json()["transaction"]["status"] == "CONFIRMED"


def test_rejected_external_ref_by_mock_provider() -> None:
    create_resp = client.post(
        "/v1/connectors/mock-bank-b/fundings",
        json={
            "transfer_id": "t-2001",
            "external_ref": "ext-cg-2001-fail",
            "amount_minor": 500,
            "currency": "USD",
            "destination": "acct-xyz",
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["status"] == "FAILED"


def test_unsupported_connector_returns_404() -> None:
    create_resp = client.post(
        "/v1/connectors/unknown-bank/payouts",
        json={
            "transfer_id": "t-3001",
            "external_ref": "ext-cg-3001",
            "amount_minor": 900,
            "currency": "USD",
            "destination": "acct-abc",
        },
    )
    assert create_resp.status_code == 404


def test_list_transactions_export() -> None:
    create_resp = client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-4001",
            "external_ref": "ext-cg-4001",
            "amount_minor": 100,
            "currency": "USD",
            "destination": "acct-list-1",
        },
    )
    assert create_resp.status_code == 201

    list_resp = client.get("/v1/connectors/transactions")
    assert list_resp.status_code == 200
    assert any(
        item["external_ref"] == "ext-cg-4001"
        and item["currency"] == "USD"
        for item in list_resp.json()
    )


def test_simulate_callback_triggers_forwarding_when_enabled(monkeypatch) -> None:
    from app.config import settings
    from app.domain import service as svc_module

    calls = {"count": 0, "external_ref": None, "status": None}
    old_enabled = settings.callback_forward_enabled

    def _fake_forward(self, txn):
        calls["count"] += 1
        calls["external_ref"] = txn.external_ref
        calls["status"] = txn.status.value
        return True

    settings.callback_forward_enabled = True
    monkeypatch.setattr(svc_module.ConnectorGatewayService, "_forward_callback_to_orchestrator", _fake_forward)

    create_resp = client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-forward-1",
            "external_ref": "ext-forward-1",
            "amount_minor": 111,
            "currency": "USD",
            "destination": "acct-forward-1",
        },
    )
    assert create_resp.status_code == 201

    simulate_resp = client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "ext-forward-1", "status": "CONFIRMED"},
    )
    assert simulate_resp.status_code == 200
    assert simulate_resp.json()["accepted"] is True
    assert calls["count"] == 1
    assert calls["external_ref"] == "ext-forward-1"
    assert calls["status"] == "CONFIRMED"

    settings.callback_forward_enabled = old_enabled


def test_transaction_events_history_and_filtering() -> None:
    create_resp = client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": "t-events-1",
            "external_ref": "ext-events-1",
            "amount_minor": 321,
            "currency": "USD",
            "destination": "acct-events-1",
        },
    )
    assert create_resp.status_code == 201

    callback_resp = client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": "ext-events-1", "status": "CONFIRMED"},
    )
    assert callback_resp.status_code == 200

    events = client.get("/v1/connectors/transaction-events", params={"external_ref": "ext-events-1"})
    assert events.status_code == 200
    assert len(events.json()) >= 2
    assert events.json()[0]["event_type"] == "CONNECTOR_TRANSACTION_SUBMITTED"
    assert any(item["event_type"] == "CONNECTOR_CALLBACK_APPLIED" for item in events.json())

    confirmed = client.get("/v1/connectors/transaction-events", params={"status": "CONFIRMED"})
    assert confirmed.status_code == 200
    assert any(item["external_ref"] == "ext-events-1" for item in confirmed.json())
