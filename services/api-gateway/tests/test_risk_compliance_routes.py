"""
Tests for risk-service and compliance-service routes exposed via the API Gateway.

All tests use monkeypatch to replace client methods with fakes that return
DummyResponse objects — no real upstream services are needed.
"""
import json
from typing import Union

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class DummyResponse:
    def __init__(self, status_code: int, body: Union[dict, list]):
        self.status_code = status_code
        self.content = json.dumps(body).encode()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _risk_routes(monkeypatch):
    """Return the routes module so monkeypatch can target _risk_client."""
    from app.api import routes
    return routes


def _compliance_routes(monkeypatch):
    from app.api import routes
    return routes


# ═══════════════════════════════════════════════════════════════════════════════
# Risk rules
# ═══════════════════════════════════════════════════════════════════════════════


def test_list_risk_rules_forwards_response(monkeypatch):
    routes = _risk_routes(monkeypatch)

    async def fake_list_rules(headers):
        return DummyResponse(200, {"rules": [], "total": 0})

    monkeypatch.setattr(routes._risk_client, "list_rules", fake_list_rules)
    resp = client.get("/v1/risk/rules")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_create_risk_rule_forwards_payload(monkeypatch):
    routes = _risk_routes(monkeypatch)
    captured = {}

    async def fake_create_rule(payload, headers):
        captured["payload"] = payload
        return DummyResponse(201, {"rule_id": "rule-abc", **payload})

    monkeypatch.setattr(routes._risk_client, "create_rule", fake_create_rule)
    rule = {"name": "Block high value", "condition_type": "amount_gt", "condition_value": "50000",
            "action": "deny", "enabled": True}
    resp = client.post("/v1/risk/rules", json=rule)
    assert resp.status_code == 201
    assert resp.json()["rule_id"] == "rule-abc"
    assert captured["payload"]["condition_type"] == "amount_gt"


def test_delete_risk_rule_forwards_rule_id(monkeypatch):
    routes = _risk_routes(monkeypatch)
    captured = {}

    async def fake_delete_rule(rule_id, headers):
        captured["rule_id"] = rule_id
        return DummyResponse(204, {})

    monkeypatch.setattr(routes._risk_client, "delete_rule", fake_delete_rule)
    resp = client.delete("/v1/risk/rules/rule-abc")
    assert resp.status_code == 204
    assert captured["rule_id"] == "rule-abc"


def test_list_risk_log_passes_query_params(monkeypatch):
    routes = _risk_routes(monkeypatch)
    captured = {}

    async def fake_list_log(params, headers):
        captured["params"] = params
        return DummyResponse(200, {"entries": [], "total": 0})

    monkeypatch.setattr(routes._risk_client, "list_log", fake_list_log)
    resp = client.get("/v1/risk/log?limit=5&decision=deny")
    assert resp.status_code == 200
    assert captured["params"]["limit"] == 5
    assert captured["params"]["decision"] == "deny"


def test_evaluate_risk_forwards_payload(monkeypatch):
    routes = _risk_routes(monkeypatch)
    captured = {}

    async def fake_evaluate(payload, headers):
        captured["payload"] = payload
        return DummyResponse(200, {"decision": "allow", "reason": None, "rule_id": None})

    monkeypatch.setattr(routes._risk_client, "evaluate", fake_evaluate)
    body = {"sender_user_id": "u-1", "recipient_phone_e164": "+15005550100", "amount_minor": 1000}
    resp = client.post("/v1/risk/evaluate", json=body)
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"
    assert captured["payload"]["sender_user_id"] == "u-1"


def test_risk_service_502_on_upstream_500(monkeypatch):
    routes = _risk_routes(monkeypatch)

    async def fake_list_rules(headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._risk_client, "list_rules", fake_list_rules)
    resp = client.get("/v1/risk/rules")
    assert resp.status_code == 502
    assert "risk" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# Compliance watchlist
# ═══════════════════════════════════════════════════════════════════════════════


def test_list_compliance_watchlist_forwards_response(monkeypatch):
    routes = _compliance_routes(monkeypatch)

    async def fake_list_watchlist(headers):
        return DummyResponse(200, {"entries": [], "total": 0})

    monkeypatch.setattr(routes._compliance_client, "list_watchlist", fake_list_watchlist)
    resp = client.get("/v1/compliance/watchlist")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_create_compliance_watchlist_entry_forwards_payload(monkeypatch):
    routes = _compliance_routes(monkeypatch)
    captured = {}

    async def fake_create(payload, headers):
        captured["payload"] = payload
        return DummyResponse(201, {"entry_id": "entry-1", **payload})

    monkeypatch.setattr(routes._compliance_client, "create_watchlist_entry", fake_create)
    entry = {"name": "John Doe", "reason_code": "OFAC-SDN"}
    resp = client.post("/v1/compliance/watchlist", json=entry)
    assert resp.status_code == 201
    assert resp.json()["entry_id"] == "entry-1"
    assert captured["payload"]["reason_code"] == "OFAC-SDN"


def test_delete_compliance_watchlist_entry_forwards_entry_id(monkeypatch):
    routes = _compliance_routes(monkeypatch)
    captured = {}

    async def fake_delete(entry_id, headers):
        captured["entry_id"] = entry_id
        return DummyResponse(204, {})

    monkeypatch.setattr(routes._compliance_client, "delete_watchlist_entry", fake_delete)
    resp = client.delete("/v1/compliance/watchlist/entry-1")
    assert resp.status_code == 204
    assert captured["entry_id"] == "entry-1"


def test_compliance_watchlist_502_on_upstream_500(monkeypatch):
    routes = _compliance_routes(monkeypatch)

    async def fake_list_watchlist(headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._compliance_client, "list_watchlist", fake_list_watchlist)
    resp = client.get("/v1/compliance/watchlist")
    assert resp.status_code == 502
    assert "compliance" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# Compliance log
# ═══════════════════════════════════════════════════════════════════════════════


def test_list_compliance_log_passes_query_params(monkeypatch):
    routes = _compliance_routes(monkeypatch)
    captured = {}

    async def fake_list_log(params, headers):
        captured["params"] = params
        return DummyResponse(200, {"entries": [], "total": 0})

    monkeypatch.setattr(routes._compliance_client, "list_log", fake_list_log)
    resp = client.get("/v1/compliance/log?limit=10&subject_type=user&decision=HIT")
    assert resp.status_code == 200
    assert captured["params"]["subject_type"] == "user"
    assert captured["params"]["decision"] == "HIT"
    assert captured["params"]["limit"] == 10


def test_list_compliance_log_default_params(monkeypatch):
    routes = _compliance_routes(monkeypatch)
    captured = {}

    async def fake_list_log(params, headers):
        captured["params"] = params
        return DummyResponse(200, {"entries": [], "total": 0})

    monkeypatch.setattr(routes._compliance_client, "list_log", fake_list_log)
    resp = client.get("/v1/compliance/log")
    assert resp.status_code == 200
    # limit has a default of 100; subject_type and decision are absent (filtered out)
    assert captured["params"]["limit"] == 100
    assert "subject_type" not in captured["params"]
    assert "decision" not in captured["params"]


# ═══════════════════════════════════════════════════════════════════════════════
# Compliance screen
# ═══════════════════════════════════════════════════════════════════════════════


def test_screen_compliance_subject_forwards_payload(monkeypatch):
    routes = _compliance_routes(monkeypatch)
    captured = {}

    async def fake_screen(payload, headers):
        captured["payload"] = payload
        return DummyResponse(
            200,
            {"decision": "CLEAR", "matched_entry_id": None, "matched_entry_name": None},
        )

    monkeypatch.setattr(routes._compliance_client, "screen", fake_screen)
    body = {"subject_name": "Jane Smith", "subject_type": "user", "subject_id": "u-99"}
    resp = client.post("/v1/compliance/screen", json=body)
    assert resp.status_code == 200
    assert resp.json()["decision"] == "CLEAR"
    assert captured["payload"]["subject_name"] == "Jane Smith"


def test_screen_compliance_hit_response_forwarded(monkeypatch):
    routes = _compliance_routes(monkeypatch)

    async def fake_screen(payload, headers):
        return DummyResponse(
            200,
            {"decision": "HIT", "matched_entry_id": "entry-1", "matched_entry_name": "Bad Actor"},
        )

    monkeypatch.setattr(routes._compliance_client, "screen", fake_screen)
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_name": "Bad Actor", "subject_type": "user", "subject_id": "u-bad"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "HIT"
    assert resp.json()["matched_entry_name"] == "Bad Actor"


def test_screen_compliance_502_on_upstream_500(monkeypatch):
    routes = _compliance_routes(monkeypatch)

    async def fake_screen(payload, headers):
        return DummyResponse(500, {"detail": "internal error"})

    monkeypatch.setattr(routes._compliance_client, "screen", fake_screen)
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_name": "X", "subject_type": "user", "subject_id": "u-1"},
    )
    assert resp.status_code == 502
    assert "compliance" in resp.json()["detail"]
