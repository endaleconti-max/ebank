"""
Gateway passthrough tests for account lifecycle endpoints:
suspend, reinstate, close, and account audit log.
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


def _user_body(account_status: str = "ACTIVE") -> dict:
    return {
        "user_id": "u-1",
        "full_name": "Test User",
        "country_code": "US",
        "email": "test@example.com",
        "account_status": account_status,
        "kyc_status": "NOT_STARTED",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


# ── Suspend ───────────────────────────────────────────────────────────────────

def test_suspend_forwards_to_identity(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_suspend(user_id, payload, headers):
        captured["user_id"] = user_id
        captured["payload"] = payload
        return DummyResponse(200, _user_body("SUSPENDED"))

    monkeypatch.setattr(routes._identity_client, "suspend_account", fake_suspend)
    resp = client.post("/v1/users/u-1/suspend", json={"reason": "Fraud investigation"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "SUSPENDED"
    assert captured["user_id"] == "u-1"
    assert captured["payload"]["reason"] == "Fraud investigation"


def test_suspend_409_forwarded(monkeypatch):
    from app.api import routes

    async def fake_suspend(user_id, payload, headers):
        return DummyResponse(409, {"detail": "cannot transition from SUSPENDED to SUSPENDED"})

    monkeypatch.setattr(routes._identity_client, "suspend_account", fake_suspend)
    resp = client.post("/v1/users/u-1/suspend", json={"reason": "Already suspended"})
    assert resp.status_code == 409


def test_suspend_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_suspend(user_id, payload, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._identity_client, "suspend_account", fake_suspend)
    resp = client.post("/v1/users/u-1/suspend", json={"reason": "Fraud"})
    assert resp.status_code == 502
    assert "identity" in resp.json()["detail"]


# ── Reinstate ─────────────────────────────────────────────────────────────────

def test_reinstate_forwards_to_identity(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_reinstate(user_id, payload, headers):
        captured["user_id"] = user_id
        captured["payload"] = payload
        return DummyResponse(200, _user_body("ACTIVE"))

    monkeypatch.setattr(routes._identity_client, "reinstate_account", fake_reinstate)
    resp = client.post("/v1/users/u-1/reinstate", json={"reason": "Investigation cleared"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "ACTIVE"
    assert captured["payload"]["reason"] == "Investigation cleared"


def test_reinstate_409_forwarded(monkeypatch):
    from app.api import routes

    async def fake_reinstate(user_id, payload, headers):
        return DummyResponse(409, {"detail": "cannot transition from ACTIVE to ACTIVE"})

    monkeypatch.setattr(routes._identity_client, "reinstate_account", fake_reinstate)
    resp = client.post("/v1/users/u-1/reinstate", json={"reason": "Never suspended"})
    assert resp.status_code == 409


# ── Close ─────────────────────────────────────────────────────────────────────

def test_close_forwards_to_identity(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_close(user_id, payload, headers):
        captured["user_id"] = user_id
        captured["payload"] = payload
        return DummyResponse(200, _user_body("CLOSED"))

    monkeypatch.setattr(routes._identity_client, "close_account", fake_close)
    resp = client.post("/v1/users/u-1/close", json={"reason": "User requested closure"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "CLOSED"
    assert captured["payload"]["reason"] == "User requested closure"


def test_close_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_close(user_id, payload, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._identity_client, "close_account", fake_close)
    resp = client.post("/v1/users/u-1/close", json={"reason": "User request"})
    assert resp.status_code == 502


# ── Account audit log ─────────────────────────────────────────────────────────

def test_get_account_audit_log_forwarded(monkeypatch):
    from app.api import routes
    captured = {}

    async def fake_log(user_id, headers):
        captured["user_id"] = user_id
        return DummyResponse(200, [
            {
                "log_id": "log-1",
                "user_id": "u-1",
                "from_status": "ACTIVE",
                "to_status": "SUSPENDED",
                "reason": "Fraud",
                "actor_id": "ops-1",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ])

    monkeypatch.setattr(routes._identity_client, "get_account_audit_log", fake_log)
    resp = client.get("/v1/users/u-1/account-audit-log")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["to_status"] == "SUSPENDED"
    assert captured["user_id"] == "u-1"


def test_get_account_audit_log_404_forwarded(monkeypatch):
    from app.api import routes

    async def fake_log(user_id, headers):
        return DummyResponse(404, {"detail": "user not found"})

    monkeypatch.setattr(routes._identity_client, "get_account_audit_log", fake_log)
    resp = client.get("/v1/users/no-such-user/account-audit-log")
    assert resp.status_code == 404


def test_get_account_audit_log_502_on_upstream_500(monkeypatch):
    from app.api import routes

    async def fake_log(user_id, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._identity_client, "get_account_audit_log", fake_log)
    resp = client.get("/v1/users/u-1/account-audit-log")
    assert resp.status_code == 502
    assert "identity" in resp.json()["detail"]
