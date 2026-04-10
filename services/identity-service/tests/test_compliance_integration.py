"""
Tests for compliance-client integration in the identity-service KYC decide flow.
"""
import json
import urllib.error
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_and_submit(full_name: str = "Test User") -> str:
    """Create a user and advance to SUBMITTED KYC state. Returns user_id."""
    user_resp = client.post(
        "/v1/users",
        json={
            "full_name": full_name,
            "country_code": "US",
            "email": f"{full_name.lower().replace(' ', '.')}@example.com",
        },
    )
    assert user_resp.status_code == 201
    user_id = user_resp.json()["user_id"]

    submit_resp = client.post(f"/v1/users/{user_id}/kyc/submit")
    assert submit_resp.json()["kyc_status"] == "SUBMITTED"
    return user_id


# ── Compliance service disabled (default) ────────────────────────────────────


def test_approve_kyc_succeeds_when_compliance_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", False
    )
    user_id = _create_and_submit()
    resp = client.post(
        f"/v1/users/{user_id}/kyc/decision",
        json={"decision": "APPROVED"},
    )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "APPROVED"


# ── Compliance service enabled: clear ────────────────────────────────────────


def test_approve_kyc_approved_when_screen_returns_clear(monkeypatch):
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    user_id = _create_and_submit("Alice Clear")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {"decision": "clear", "matched_entry_id": None, "matched_entry_name": None}
        ).encode()

        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "APPROVED"},
        )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "APPROVED"


# ── Compliance service enabled: hit overrides approval ───────────────────────


def test_approve_kyc_overridden_to_rejected_when_screen_returns_hit(monkeypatch):
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    user_id = _create_and_submit("Vladmir Badguy")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {
                "decision": "hit",
                "matched_entry_id": "entry-abc",
                "matched_entry_name": "Vladmir Badguy",
            }
        ).encode()

        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "APPROVED"},
        )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "REJECTED"


# ── Compliance service enabled: potential_match does not block ────────────────


def test_approve_kyc_proceeds_when_screen_returns_potential_match(monkeypatch):
    """potential_match is advisory — KYC approval is not automatically blocked."""
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    user_id = _create_and_submit("Jahn Doe")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {
                "decision": "potential_match",
                "matched_entry_id": "entry-xyz",
                "matched_entry_name": "John Doe",
            }
        ).encode()

        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "APPROVED"},
        )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "APPROVED"


# ── Fallback: compliance service unreachable with allow policy ────────────────


def test_approve_kyc_succeeds_when_compliance_unreachable_allow_policy(monkeypatch):
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    monkeypatch.setattr(
        "app.domain.service.settings.compliance_service_fallback_policy", "allow"
    )
    user_id = _create_and_submit("Bob Normal")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "APPROVED"},
        )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "APPROVED"


# ── Fallback: compliance service unreachable with deny policy ─────────────────


def test_approve_kyc_rejected_when_compliance_unreachable_deny_policy(monkeypatch):
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    monkeypatch.setattr(
        "app.domain.service.settings.compliance_service_fallback_policy", "deny"
    )
    user_id = _create_and_submit("Carol Safe")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "APPROVED"},
        )
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "REJECTED"


# ── Explicit reject is never sent to compliance service ──────────────────────


def test_explicit_reject_does_not_call_compliance(monkeypatch):
    """Operator-initiated REJECTED decisions skip screening (no approval to block)."""
    monkeypatch.setattr(
        "app.domain.compliance_client.settings.compliance_service_enabled", True
    )
    user_id = _create_and_submit("Dave Rejected")
    with patch(
        "app.domain.compliance_client.urllib.request.urlopen"
    ) as mock_open:
        resp = client.post(
            f"/v1/users/{user_id}/kyc/decision",
            json={"decision": "REJECTED"},
        )
        mock_open.assert_not_called()
    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "REJECTED"
