"""
Tests for account lifecycle management:
suspend, reinstate, close, and account audit log endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_user(email: str = "lifecycle@example.com") -> dict:
    resp = client.post("/v1/users", json={
        "full_name": "Test User",
        "country_code": "US",
        "email": email,
    })
    assert resp.status_code == 201
    return resp.json()


# ── Suspend ───────────────────────────────────────────────────────────────────

def test_suspend_active_user():
    user = _create_user("suspend1@example.com")
    resp = client.post(
        f"/v1/users/{user['user_id']}/suspend",
        json={"reason": "Fraud investigation"},
    )
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "SUSPENDED"


def test_suspend_returns_full_user_response():
    user = _create_user("suspend2@example.com")
    resp = client.post(
        f"/v1/users/{user['user_id']}/suspend",
        json={"reason": "Fraud investigation"},
    )
    body = resp.json()
    assert body["user_id"] == user["user_id"]
    assert body["account_status"] == "SUSPENDED"
    assert "kyc_status" in body


def test_suspend_already_suspended_returns_409():
    user = _create_user("suspend3@example.com")
    client.post(f"/v1/users/{user['user_id']}/suspend", json={"reason": "First"})
    resp = client.post(f"/v1/users/{user['user_id']}/suspend", json={"reason": "Second"})
    assert resp.status_code == 409


def test_suspend_closed_user_returns_409():
    user = _create_user("suspend4@example.com")
    client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "Closed"})
    resp = client.post(f"/v1/users/{user['user_id']}/suspend", json={"reason": "Too late"})
    assert resp.status_code == 409


def test_suspend_unknown_user_returns_404():
    resp = client.post("/v1/users/no-such-user/suspend", json={"reason": "Fraud check"})
    assert resp.status_code == 404


def test_suspend_missing_reason_returns_422():
    user = _create_user("suspend5@example.com")
    resp = client.post(f"/v1/users/{user['user_id']}/suspend", json={})
    assert resp.status_code == 422


# ── Reinstate ─────────────────────────────────────────────────────────────────

def test_reinstate_suspended_user():
    user = _create_user("reinstate1@example.com")
    client.post(f"/v1/users/{user['user_id']}/suspend", json={"reason": "Suspend"})
    resp = client.post(f"/v1/users/{user['user_id']}/reinstate", json={"reason": "Cleared"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "ACTIVE"


def test_reinstate_active_user_returns_409():
    user = _create_user("reinstate2@example.com")
    resp = client.post(f"/v1/users/{user['user_id']}/reinstate", json={"reason": "Never suspended"})
    assert resp.status_code == 409


def test_reinstate_closed_user_returns_409():
    user = _create_user("reinstate3@example.com")
    client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "Closed"})
    resp = client.post(f"/v1/users/{user['user_id']}/reinstate", json={"reason": "Try to reopen"})
    assert resp.status_code == 409


def test_reinstate_unknown_user_returns_404():
    resp = client.post("/v1/users/no-such-user/reinstate", json={"reason": "False alarm"})
    assert resp.status_code == 404


# ── Close ─────────────────────────────────────────────────────────────────────

def test_close_active_user():
    user = _create_user("close1@example.com")
    resp = client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "User requested"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "CLOSED"


def test_close_suspended_user():
    user = _create_user("close2@example.com")
    client.post(f"/v1/users/{user['user_id']}/suspend", json={"reason": "Fraud"})
    resp = client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "Confirmed"})
    assert resp.status_code == 200
    assert resp.json()["account_status"] == "CLOSED"


def test_close_already_closed_returns_409():
    user = _create_user("close3@example.com")
    client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "First"})
    resp = client.post(f"/v1/users/{user['user_id']}/close", json={"reason": "Second"})
    assert resp.status_code == 409


def test_close_unknown_user_returns_404():
    resp = client.post("/v1/users/no-such-user/close", json={"reason": "User request"})
    assert resp.status_code == 404


# ── Account audit log ─────────────────────────────────────────────────────────

def test_audit_log_empty_for_new_user():
    user = _create_user("audit1@example.com")
    resp = client.get(f"/v1/users/{user['user_id']}/account-audit-log")
    assert resp.status_code == 200
    assert resp.json() == []


def test_audit_log_records_suspend_then_reinstate():
    user = _create_user("audit2@example.com")
    uid = user["user_id"]
    client.post(f"/v1/users/{uid}/suspend",
                json={"reason": "Fraud"},
                headers={"X-Caller-Id": "ops-agent-1"})
    client.post(f"/v1/users/{uid}/reinstate",
                json={"reason": "Cleared"},
                headers={"X-Caller-Id": "ops-agent-2"})

    resp = client.get(f"/v1/users/{uid}/account-audit-log")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2

    assert entries[0]["from_status"] == "ACTIVE"
    assert entries[0]["to_status"] == "SUSPENDED"
    assert entries[0]["reason"] == "Fraud"
    assert entries[0]["actor_id"] == "ops-agent-1"

    assert entries[1]["from_status"] == "SUSPENDED"
    assert entries[1]["to_status"] == "ACTIVE"
    assert entries[1]["actor_id"] == "ops-agent-2"


def test_audit_log_records_actor_id_from_header():
    user = _create_user("audit3@example.com")
    uid = user["user_id"]
    client.post(
        f"/v1/users/{uid}/close",
        json={"reason": "User request"},
        headers={"X-Caller-Id": "admin-portal"},
    )
    entries = client.get(f"/v1/users/{uid}/account-audit-log").json()
    assert entries[0]["actor_id"] == "admin-portal"


def test_audit_log_defaults_actor_to_unknown():
    user = _create_user("audit4@example.com")
    uid = user["user_id"]
    client.post(f"/v1/users/{uid}/suspend", json={"reason": "Auto rule"})
    entries = client.get(f"/v1/users/{uid}/account-audit-log").json()
    assert entries[0]["actor_id"] == "unknown"


def test_audit_log_unknown_user_returns_404():
    resp = client.get("/v1/users/no-such-user/account-audit-log")
    assert resp.status_code == 404


def test_status_check_reflects_suspension():
    """GET /users/{id}/status should show SUSPENDED after suspend call."""
    user = _create_user("statuscheck1@example.com")
    uid = user["user_id"]
    client.post(f"/v1/users/{uid}/suspend", json={"reason": "check"})
    resp = client.get(f"/v1/users/{uid}/status")
    assert resp.json()["account_status"] == "SUSPENDED"
