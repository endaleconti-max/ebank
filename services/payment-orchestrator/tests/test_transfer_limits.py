"""
Tests for transfer limit enforcement by KYC tier.
"""
import pytest

from app.domain.prechecks import run_prechecks


def test_transfer_within_approved_limit_passes(monkeypatch):
    """Sender with APPROVED KYC, amount within limit."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch

    with patch("app.domain.identity_client._urlopen") as id_mock:
        import json
        id_mock.return_value.__enter__ = lambda s: s
        id_mock.return_value.__exit__ = lambda s, *a: False
        id_mock.return_value.read.return_value = json.dumps(
            {"account_status": "ACTIVE", "kyc_status": "APPROVED"}
        ).encode()

        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=100_000,  # within APPROVED limit of 500,000
            note=None,
        )
    assert ok is True


def test_transfer_exceeds_approved_limit_fails(monkeypatch):
    """Sender with APPROVED KYC, amount exceeds limit."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch
    import json

    with patch("app.domain.identity_client._urlopen") as id_mock:
        id_mock.return_value.__enter__ = lambda s: s
        id_mock.return_value.__exit__ = lambda s, *a: False
        id_mock.return_value.read.return_value = json.dumps(
            {"account_status": "ACTIVE", "kyc_status": "APPROVED"}
        ).encode()

        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=600_000,  # exceeds APPROVED limit of 500,000
            note=None,
        )
    assert ok is False
    assert "transfer_limit_exceeded" in reason


def test_transfer_within_not_started_limit_passes(monkeypatch):
    """Sender identity unavailable, fallback to NOT_STARTED tier, within limit."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.identity_service_fallback_policy", "allow")
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch
    import urllib.error

    with patch(
        "app.domain.identity_client._urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=5_000,  # within NOT_STARTED limit of 10,000
            note=None,
        )
    assert ok is True


def test_transfer_exceeds_not_started_limit_fails(monkeypatch):
    """Sender identity unavailable, fallback to NOT_STARTED tier, exceeds limit."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.identity_service_fallback_policy", "allow")
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch
    import urllib.error

    with patch(
        "app.domain.identity_client._urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=15_000,  # exceeds NOT_STARTED limit of 10,000
            note=None,
        )
    assert ok is False
    assert "transfer_limit_exceeded" in reason


def test_transfer_limits_disabled_high_amount_passes(monkeypatch):
    """Transfer limits disabled, no check applied."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", False)

    from unittest.mock import patch
    import json

    with patch("app.domain.identity_client._urlopen") as id_mock:
        id_mock.return_value.__enter__ = lambda s: s
        id_mock.return_value.__exit__ = lambda s, *a: False
        id_mock.return_value.read.return_value = json.dumps(
            {"account_status": "ACTIVE", "kyc_status": "APPROVED"}  # Use APPROVED so KYC check passes
        ).encode()

        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=1_000_000,  # way over any limit
            note=None,
        )
    assert ok is True  # passes because limits_enabled=False


def test_transfer_with_rejected_kyc_fails(monkeypatch):
    """Sender with REJECTED KYC (limit=0) cannot transfer."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", False)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch
    import json

    with patch("app.domain.identity_client._urlopen") as id_mock:
        id_mock.return_value.__enter__ = lambda s: s
        id_mock.return_value.__exit__ = lambda s, *a: False
        id_mock.return_value.read.return_value = json.dumps(
            # REJECTED KYC is blocked earlier, but if it somehow gets here, should fail on limit
            {"account_status": "ACTIVE", "kyc_status": "REJECTED"}
        ).encode()

        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=1_000,  # any amount exceeds REJECTED limit of 0
            note=None,
        )
    # First it should be blocked by KYC check, not limit check
    # But if it somehow gets to limit check, it should fail
    assert ok is False


def test_transfer_limit_check_before_risk_service(monkeypatch):
    """Transfer limit is checked before calling risk-service."""
    monkeypatch.setattr("app.domain.identity_client.settings.identity_service_enabled", True)
    monkeypatch.setattr("app.domain.alias_client.settings.alias_service_enabled", False)
    monkeypatch.setattr("app.domain.risk_client.settings.risk_service_enabled", True)
    monkeypatch.setattr("app.domain.prechecks.settings.transfer_limits_enabled", True)

    from unittest.mock import patch
    import json

    risk_called = {"count": 0}

    original_call_risk = None

    def fake_call_risk(*args, **kwargs):
        risk_called["count"] += 1
        return None

    with patch("app.domain.identity_client._urlopen") as id_mock, \
         patch("app.domain.risk_client.call_risk_service", side_effect=fake_call_risk):

        id_mock.return_value.__enter__ = lambda s: s
        id_mock.return_value.__exit__ = lambda s, *a: False
        id_mock.return_value.read.return_value = json.dumps(
            {"account_status": "ACTIVE", "kyc_status": "APPROVED"}
        ).encode()

        ok, reason = run_prechecks(
            sender_user_id="u-1",
            recipient_phone_e164="+15005550100",
            amount_minor=600_000,  # exceeds APPROVED limit
            note=None,
        )

    # Should fail on limit check before calling risk-service
    assert ok is False
    assert risk_called["count"] == 0  # risk service not called


def test_different_kyc_tiers_have_different_limits(monkeypatch):
    """Verify each KYC tier has appropriate limits."""
    limits = {
        "NOT_STARTED": 10_000,
        "SUBMITTED": 10_000,
        "APPROVED": 500_000,
        "REJECTED": 0,
    }

    from app.domain.prechecks import check_transfer_limits

    for kyc_status, expected_limit in limits.items():
        # Transfer at limit - should fail if > limit
        within = expected_limit - 1
        exceeded = expected_limit + 1

        # Within limit should pass (or be disabled)
        ok, _ = check_transfer_limits(kyc_status, within)
        assert ok is True, f"{kyc_status}: amount {within} should be within limit {expected_limit}"

        # Exceeding limit should fail
        ok, reason = check_transfer_limits(kyc_status, exceeded)
        assert ok is False, f"{kyc_status}: amount {exceeded} should exceed limit {expected_limit}"
        assert "transfer_limit_exceeded" in reason
