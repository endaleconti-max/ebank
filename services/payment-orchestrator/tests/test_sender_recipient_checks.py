"""
Tests for sender-KYC and recipient-alias checks wired into orchestrator prechecks.
"""
import json
import urllib.error
from unittest.mock import patch

import pytest

from app.domain.prechecks import run_prechecks


def _run(
    *,
    sender: str = "user-ok",
    recipient: str = "+15005550100",
    amount: int = 1000,
    note=None,
):
    return run_prechecks(
        sender_user_id=sender,
        recipient_phone_e164=recipient,
        amount_minor=amount,
        note=note,
    )


# ── Identity + alias services disabled (default) ─────────────────────────────


def test_all_checks_pass_when_services_disabled(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    ok, reason = _run()
    assert ok is True


# ── Identity checks ───────────────────────────────────────────────────────────


def _mock_identity(account_status: str, kyc_status: str):
    """Return a context manager that patches urlopen for an identity-service status call."""
    return patch("app.domain.identity_client._urlopen")


def _configure_identity_mock(mock_open, account_status: str, kyc_status: str):
    mock_open.return_value.__enter__ = lambda s: s
    mock_open.return_value.__exit__ = lambda s, *a: False
    mock_open.return_value.read.return_value = json.dumps(
        {"account_status": account_status, "kyc_status": kyc_status}
    ).encode()


def test_sender_inactive_account_blocked(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch("app.domain.identity_client._urlopen") as mock_open:
        _configure_identity_mock(mock_open, "SUSPENDED", "APPROVED")
        ok, reason = _run()
    assert ok is False
    assert "sender_account_not_active" in reason
    assert "SUSPENDED" in reason


def test_sender_kyc_not_approved_blocked(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch("app.domain.identity_client._urlopen") as mock_open:
        _configure_identity_mock(mock_open, "ACTIVE", "SUBMITTED")
        ok, reason = _run()
    assert ok is False
    assert "sender_kyc_not_approved" in reason


def test_sender_active_and_approved_passes(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch("app.domain.identity_client._urlopen") as mock_open:
        _configure_identity_mock(mock_open, "ACTIVE", "APPROVED")
        ok, reason = _run()
    assert ok is True


def test_identity_unavailable_allow_policy_passes(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.identity_service_fallback_policy", "allow")
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch(
        "app.domain.identity_client._urlopen",
        side_effect=urllib.error.URLError("refused"),
    ):
        ok, reason = _run()
    assert ok is True


def test_identity_unavailable_deny_policy_fails(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.identity_service_fallback_policy", "deny")
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch(
        "app.domain.identity_client._urlopen",
        side_effect=urllib.error.URLError("refused"),
    ):
        ok, reason = _run()
    assert ok is False
    assert "identity_service_unavailable" in reason


# ── Alias checks ──────────────────────────────────────────────────────────────


def _configure_alias_mock(mock_open, user_id: str, alias_id: str):
    mock_open.return_value.__enter__ = lambda s: s
    mock_open.return_value.__exit__ = lambda s, *a: False
    mock_open.return_value.read.return_value = json.dumps(
        {"user_id": user_id, "alias_id": alias_id}
    ).encode()


def test_recipient_alias_found_passes(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch("app.domain.alias_client._urlopen") as mock_open:
        _configure_alias_mock(mock_open, "user-recipient", "alias-xyz")
        ok, reason = _run()
    assert ok is True


def test_recipient_alias_not_found_blocks(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch("app.domain.alias_client._urlopen", side_effect=err):
        ok, reason = _run()
    assert ok is False
    assert "recipient_alias_not_found" in reason


def test_recipient_alias_empty_user_id_blocks(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch("app.domain.alias_client._urlopen") as mock_open:
        _configure_alias_mock(mock_open, "", "")
        ok, reason = _run()
    assert ok is False
    assert "recipient_alias_not_found" in reason


def test_alias_unavailable_allow_policy_passes(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.alias_service_fallback_policy", "allow")
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch(
        "app.domain.alias_client._urlopen",
        side_effect=urllib.error.URLError("refused"),
    ):
        ok, reason = _run()
    assert ok is True


def test_alias_unavailable_deny_policy_fails(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", False)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.alias_service_fallback_policy", "deny")
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    with patch(
        "app.domain.alias_client._urlopen",
        side_effect=urllib.error.URLError("refused"),
    ):
        ok, reason = _run()
    assert ok is False
    assert "alias_service_unavailable" in reason


# ── Combined: all services enabled ───────────────────────────────────────────


def test_all_services_enabled_full_happy_path(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)

    with patch("app.domain.identity_client._urlopen") as id_mock, \
         patch("app.domain.alias_client._urlopen") as alias_mock, \
         patch("app.domain.risk_client._urlopen") as risk_mock:

        _configure_identity_mock(id_mock, "ACTIVE", "APPROVED")
        _configure_alias_mock(alias_mock, "user-recipient", "alias-abc")
        risk_mock.return_value.__enter__ = lambda s: s
        risk_mock.return_value.__exit__ = lambda s, *a: False
        risk_mock.return_value.read.return_value = json.dumps(
            {"decision": "allow", "reason": None}
        ).encode()

        ok, reason = _run()
    assert ok is True


def test_all_services_enabled_blocked_by_identity(monkeypatch):
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", True)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)

    with patch("app.domain.identity_client._urlopen") as id_mock, \
         patch("app.domain.alias_client._urlopen") as alias_mock:

        _configure_identity_mock(id_mock, "ACTIVE", "NOT_STARTED")
        # alias mock should NOT be called; if it is, we want it to succeed anyway
        _configure_alias_mock(alias_mock, "user-recipient", "alias-abc")

        ok, reason = _run()
    assert ok is False
    assert "sender_kyc_not_approved" in reason
