"""
Tests for the orchestrator's risk-client integration in prechecks.

These tests verify:
1. When risk_service_enabled=False, local prechecks still work correctly.
2. When risk_service_enabled=True and remote returns deny, transfer fails.
3. When risk_service_enabled=True and remote returns allow, transfer proceeds.
4. When risk_service_enabled=True and remote is unreachable (connection refused),
   the fallback to local prechecks is used transparently.
"""
import json
from typing import Optional
from unittest.mock import patch

import pytest

from app.domain.prechecks import run_prechecks


# ── Helpers ────────────────────────────────────────────────────────────────────


def _run(
    *,
    sender: str = "user-ok",
    recipient: str = "+15005550100",
    amount: int = 1000,
    note: Optional[str] = None,
    caller_id: Optional[str] = None,
):
    return run_prechecks(
        sender_user_id=sender,
        recipient_phone_e164=recipient,
        amount_minor=amount,
        note=note,
        caller_id=caller_id,
    )


# ── Local fallback (risk_service_enabled=False) ────────────────────────────────


def test_local_precheck_allows_normal_transfer(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    ok, reason = _run()
    assert ok is True
    assert reason is None


def test_local_precheck_denies_large_amount(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.risk_amount_limit_minor", 100)
    ok, reason = _run(amount=101)
    assert ok is False
    assert "risk_precheck_failed" in reason


def test_local_precheck_denies_fraud_note(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    ok, reason = _run(note="this is a fraud transfer")
    assert ok is False
    assert "risk_precheck_failed" in reason


def test_local_precheck_denies_blocked_sender(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    ok, reason = _run(sender="blocked-userX")
    assert ok is False
    assert "compliance_precheck_failed" in reason


def test_local_precheck_denies_blocked_recipient(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    ok, reason = _run(recipient="+9991234567")
    assert ok is False
    assert "compliance_precheck_failed" in reason


# ── Remote risk-service (risk_service_enabled=True) ───────────────────────────


def test_remote_deny_fails_precheck(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    with patch(
        "app.domain.risk_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {"decision": "deny", "reason": "rule:abc:limit_rule"}
        ).encode()

        ok, reason = _run()
        assert ok is False
        assert "risk_service_denied" in reason
        assert "limit_rule" in reason


def test_remote_allow_passes_precheck(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    with patch(
        "app.domain.risk_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {"decision": "allow", "reason": None}
        ).encode()

        ok, reason = _run()
        assert ok is True


def test_remote_review_passes_precheck(monkeypatch):
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    with patch(
        "app.domain.risk_client.urllib.request.urlopen"
    ) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = lambda s, *a: False
        mock_open.return_value.read.return_value = json.dumps(
            {"decision": "review", "reason": "rule:xyz:suspicious_note"}
        ).encode()

        ok, reason = _run()
        assert ok is True  # review = pass validation


def test_remote_unavailable_falls_back_to_local_allow(monkeypatch):
    """Connection refused → fall back to local checks → allow normal transfer."""
    import urllib.error
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    with patch(
        "app.domain.risk_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        ok, reason = _run(amount=500)  # within local limit
        assert ok is True


def test_remote_unavailable_falls_back_to_local_deny(monkeypatch):
    """Connection refused → fall back to local checks → deny blocked sender."""
    import urllib.error
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    with patch(
        "app.domain.risk_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        ok, reason = _run(sender="blocked-userX")
        assert ok is False
        assert "compliance_precheck_failed" in reason
