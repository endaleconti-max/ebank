"""
Gateway passthrough tests for ledger-service endpoints:
create account, get balance, and get entry.
"""
import json
from typing import Union

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class DummyResponse:
    def __init__(self, status_code: int, body: Union[dict, list]):
        self.status_code = status_code
        self.content = json.dumps(body).encode()


# ── Create account ────────────────────────────────────────────────────────────

def test_create_ledger_account_forwards_payload(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_create(payload, headers):
        captured["payload"] = payload
        return DummyResponse(201, {
            "account_id": "acc-1",
            "owner_type": "user",
            "owner_id": "u-1",
            "account_type": "USER_AVAILABLE",
            "currency": "USD",
            "status": "ACTIVE",
            "created_at": "2026-01-01T00:00:00Z",
        })

    monkeypatch.setattr(routes._ledger_client, "create_account", fake_create)
    resp = client.post("/v1/ledger/accounts", json={
        "owner_type": "user",
        "owner_id": "u-1",
        "account_type": "USER_AVAILABLE",
        "currency": "USD",
    })
    assert resp.status_code == 201
    assert resp.json()["account_id"] == "acc-1"
    assert captured["payload"]["owner_id"] == "u-1"


def test_create_ledger_account_409_forwarded(monkeypatch):
    from app.api import routes

    async def fake_create(payload, headers):
        return DummyResponse(409, {"detail": "account already exists"})

    monkeypatch.setattr(routes._ledger_client, "create_account", fake_create)
    resp = client.post("/v1/ledger/accounts", json={
        "owner_type": "user",
        "owner_id": "u-1",
        "account_type": "USER_AVAILABLE",
        "currency": "USD",
    })
    assert resp.status_code == 409


def test_create_ledger_account_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_create(payload, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._ledger_client, "create_account", fake_create)
    resp = client.post("/v1/ledger/accounts", json={
        "owner_type": "user",
        "owner_id": "u-1",
        "account_type": "USER_AVAILABLE",
        "currency": "USD",
    })
    assert resp.status_code == 502
    assert "ledger" in resp.json()["detail"]


# ── Get balance ───────────────────────────────────────────────────────────────

def test_get_ledger_balance_forwards_account_id(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_get_balance(account_id, headers):
        captured["account_id"] = account_id
        return DummyResponse(200, {
            "account_id": account_id,
            "currency": "USD",
            "balance_minor": 50000,
        })

    monkeypatch.setattr(routes._ledger_client, "get_balance", fake_get_balance)
    resp = client.get("/v1/ledger/accounts/acc-1/balance")
    assert resp.status_code == 200
    assert resp.json()["balance_minor"] == 50000
    assert captured["account_id"] == "acc-1"


def test_get_ledger_balance_404_forwarded(monkeypatch):
    from app.api import routes

    async def fake_get_balance(account_id, headers):
        return DummyResponse(404, {"detail": "account not found"})

    monkeypatch.setattr(routes._ledger_client, "get_balance", fake_get_balance)
    resp = client.get("/v1/ledger/accounts/no-such-account/balance")
    assert resp.status_code == 404


def test_get_ledger_balance_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_get_balance(account_id, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._ledger_client, "get_balance", fake_get_balance)
    resp = client.get("/v1/ledger/accounts/acc-1/balance")
    assert resp.status_code == 502
    assert "ledger" in resp.json()["detail"]


# ── Get entry ─────────────────────────────────────────────────────────────────

def test_get_ledger_entry_forwards_entry_id(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_get_entry(entry_id, headers):
        captured["entry_id"] = entry_id
        return DummyResponse(200, {
            "entry_id": entry_id,
            "external_ref": "transfer-1",
            "transfer_id": "t-1",
            "entry_type": "TRANSFER",
            "created_at": "2026-01-01T00:00:00Z",
            "postings": [
                {
                    "posting_id": "posting-1",
                    "account_id": "acc-sender",
                    "direction": "DEBIT",
                    "amount_minor": 10000,
                    "currency": "USD",
                },
                {
                    "posting_id": "posting-2",
                    "account_id": "acc-transit",
                    "direction": "CREDIT",
                    "amount_minor": 10000,
                    "currency": "USD",
                }
            ],
        })

    monkeypatch.setattr(routes._ledger_client, "get_entry", fake_get_entry)
    resp = client.get("/v1/ledger/entries/entry-1")
    assert resp.status_code == 200
    entry = resp.json()
    assert entry["entry_type"] == "TRANSFER"
    assert len(entry["postings"]) == 2
    assert captured["entry_id"] == "entry-1"


def test_get_ledger_entry_404_forwarded(monkeypatch):
    from app.api import routes

    async def fake_get_entry(entry_id, headers):
        return DummyResponse(404, {"detail": "entry not found"})

    monkeypatch.setattr(routes._ledger_client, "get_entry", fake_get_entry)
    resp = client.get("/v1/ledger/entries/no-such-entry")
    assert resp.status_code == 404


def test_get_ledger_entry_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_get_entry(entry_id, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._ledger_client, "get_entry", fake_get_entry)
    resp = client.get("/v1/ledger/entries/entry-1")
    assert resp.status_code == 502
    assert "ledger" in resp.json()["detail"]
