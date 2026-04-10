"""
Tests for the risk-service API.

Uses an in-memory SQLite database per test via a fixture that overrides
the get_db dependency.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models import Base, get_db
from app.main import app

# ── In-memory DB fixture ──────────────────────────────────────────────────────

TEST_DB_URL = "sqlite://"  # in-memory, per-connection


@pytest.fixture()
def client():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Evaluate ──────────────────────────────────────────────────────────────────


def test_evaluate_allows_normal_transfer(client):
    """When no rules are configured and amount is within default limit, decision is allow."""
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 500,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["risk_score"] == 0
    assert body["applied_rule_id"] is None


def test_evaluate_denies_by_default_limit(client):
    """Amount exceeding the default 1,000,000 minor units is denied without any rules."""
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 1_000_001,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "deny"
    assert body["reason"] == "default_limit_exceeded"
    assert body["risk_score"] == 100


def test_evaluate_denies_by_amount_gt_rule(client):
    """A custom amount_gt rule fires before the default limit check."""
    # Create a rule: deny when amount > 100
    r = client.post(
        "/v1/risk/rules",
        json={
            "name": "low_limit",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    assert r.status_code == 201
    rule_id = r.json()["rule_id"]

    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 101,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "deny"
    assert body["applied_rule_id"] == rule_id
    assert rule_id in body["reason"]
    assert body["risk_score"] == 100


def test_evaluate_reviews_by_note_keyword_rule(client):
    """A note_keyword rule matching on note returns review decision."""
    client.post(
        "/v1/risk/rules",
        json={
            "name": "suspicious_note",
            "condition_type": "note_keyword",
            "condition_value": "urgent",
            "action": "review",
            "enabled": True,
        },
    )
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 50,
            "note": "Please do this URGENT transfer",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "review"
    assert body["risk_score"] == 50


def test_evaluate_denies_by_sender_prefix_rule(client):
    """sender_prefix condition matches on sender_user_id prefix."""
    client.post(
        "/v1/risk/rules",
        json={
            "name": "block_test_senders",
            "condition_type": "sender_prefix",
            "condition_value": "blocked-",
            "action": "deny",
            "enabled": True,
        },
    )
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "blocked-userX",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 10,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "deny"


def test_evaluate_allows_when_sender_prefix_not_matched(client):
    """sender_prefix rule does not fire for non-matching sender."""
    client.post(
        "/v1/risk/rules",
        json={
            "name": "block_test_senders",
            "condition_type": "sender_prefix",
            "condition_value": "blocked-",
            "action": "deny",
            "enabled": True,
        },
    )
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "good-userY",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 10,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


def test_disabled_rule_is_skipped(client):
    """A disabled rule must not fire in evaluation."""
    client.post(
        "/v1/risk/rules",
        json={
            "name": "disabled_rule",
            "condition_type": "amount_gt",
            "condition_value": "1",
            "action": "deny",
            "enabled": False,
        },
    )
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 99,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


def test_first_matching_rule_wins(client):
    """When multiple rules match, only the first (eldest by created_at) fires."""
    client.post(
        "/v1/risk/rules",
        json={
            "name": "rule_deny",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    r2 = client.post(
        "/v1/risk/rules",
        json={
            "name": "rule_review",
            "condition_type": "amount_gt",
            "condition_value": "50",
            "action": "review",
            "enabled": True,
        },
    )
    r2_id = r2.json()["rule_id"]

    # amount_minor=200 matches both rules; rule_deny was created first
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 200,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # First rule in created_at order matches, should NOT be r2
    assert body["applied_rule_id"] != r2_id


# ── Rule CRUD ─────────────────────────────────────────────────────────────────


def test_create_rule_success(client):
    resp = client.post(
        "/v1/risk/rules",
        json={
            "name": "test_rule",
            "condition_type": "amount_gt",
            "condition_value": "5000",
            "action": "deny",
            "enabled": True,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "test_rule"
    assert body["condition_type"] == "amount_gt"
    assert body["rule_id"] is not None


def test_create_rule_invalid_condition_type_rejected(client):
    resp = client.post(
        "/v1/risk/rules",
        json={
            "name": "bad",
            "condition_type": "nonexistent_type",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_create_rule_invalid_action_rejected(client):
    resp = client.post(
        "/v1/risk/rules",
        json={
            "name": "bad",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "allow",  # not a valid action
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_create_rule_empty_condition_value_rejected(client):
    resp = client.post(
        "/v1/risk/rules",
        json={
            "name": "bad",
            "condition_type": "amount_gt",
            "condition_value": "",
            "action": "deny",
            "enabled": True,
        },
    )
    assert resp.status_code == 422


def test_list_rules_returns_all(client):
    client.post(
        "/v1/risk/rules",
        json={
            "name": "r1",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    client.post(
        "/v1/risk/rules",
        json={
            "name": "r2",
            "condition_type": "note_keyword",
            "condition_value": "spam",
            "action": "review",
            "enabled": False,
        },
    )
    resp = client.get("/v1/risk/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    names = {r["name"] for r in body["rules"]}
    assert names == {"r1", "r2"}


def test_list_rules_enabled_only_filter(client):
    client.post(
        "/v1/risk/rules",
        json={
            "name": "enabled",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    client.post(
        "/v1/risk/rules",
        json={
            "name": "disabled",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": False,
        },
    )
    resp = client.get("/v1/risk/rules?enabled_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["rules"][0]["name"] == "enabled"


def test_delete_rule_returns_204(client):
    r = client.post(
        "/v1/risk/rules",
        json={
            "name": "to_delete",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    rule_id = r.json()["rule_id"]
    resp = client.delete(f"/v1/risk/rules/{rule_id}")
    assert resp.status_code == 204


def test_delete_nonexistent_rule_returns_404(client):
    resp = client.delete("/v1/risk/rules/no-such-rule")
    assert resp.status_code == 404


def test_deleted_rule_no_longer_listed(client):
    r = client.post(
        "/v1/risk/rules",
        json={
            "name": "to_delete",
            "condition_type": "amount_gt",
            "condition_value": "100",
            "action": "deny",
            "enabled": True,
        },
    )
    rule_id = r.json()["rule_id"]
    client.delete(f"/v1/risk/rules/{rule_id}")
    resp = client.get("/v1/risk/rules")
    assert resp.json()["total"] == 0


# ── Evaluation log ────────────────────────────────────────────────────────────


def test_evaluation_log_records_entry(client):
    client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-log-test",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 10,
        },
    )
    resp = client.get("/v1/risk/log?sender_user_id=user-log-test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["entries"][0]["sender_user_id"] == "user-log-test"
    assert body["entries"][0]["decision"] == "allow"


def test_evaluation_log_filters_by_decision(client):
    # Generate one allow + one deny (via rule)
    client.post(
        "/v1/risk/rules",
        json={
            "name": "deny_large",
            "condition_type": "amount_gt",
            "condition_value": "500",
            "action": "deny",
            "enabled": True,
        },
    )
    client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 10,
        },
    )
    client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 5000,
        },
    )

    deny_resp = client.get("/v1/risk/log?decision=deny")
    assert deny_resp.status_code == 200
    deny_body = deny_resp.json()
    assert deny_body["total"] == 1
    assert deny_body["entries"][0]["decision"] == "deny"

    allow_resp = client.get("/v1/risk/log?decision=allow")
    assert allow_resp.json()["total"] == 1


def test_evaluate_missing_required_fields_rejected(client):
    resp = client.post("/v1/risk/evaluate", json={"sender_user_id": "user-abc"})
    assert resp.status_code == 422


def test_evaluate_zero_amount_rejected(client):
    resp = client.post(
        "/v1/risk/evaluate",
        json={
            "sender_user_id": "user-abc",
            "recipient_phone_e164": "+15005550100",
            "amount_minor": 0,
        },
    )
    assert resp.status_code == 422
