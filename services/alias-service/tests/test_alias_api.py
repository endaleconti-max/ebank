import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


PHONE = "+15550001234"
OTP = "654321"


def _do_two_step_verify() -> str:
    """Runs the two-step OTP verification and returns verification_id."""
    client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    resp = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    assert resp.json()["verified"] is True
    return resp.json()["verification_id"]


def test_verify_bind_and_resolve() -> None:
    verification_id = _do_two_step_verify()

    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-001", "discoverable": True},
    )
    assert bind_resp.status_code == 201
    alias_id = bind_resp.json()["alias_id"]
    assert bind_resp.json()["status"] == "BOUND"
    assert bind_resp.json()["user_id"] == "u-001"

    resolve_resp = client.get("/v1/aliases/resolve", params={"phone_e164": PHONE})
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["found"] is True
    assert resolve_resp.json()["alias"]["alias_id"] == alias_id

    unbind_resp = client.post(
        f"/v1/aliases/{alias_id}/unbind",
        json={"reason_code": "user-request"},
    )
    assert unbind_resp.status_code == 200
    assert unbind_resp.json()["status"] == "UNBOUND"

    resolve_after = client.get("/v1/aliases/resolve", params={"phone_e164": PHONE})
    assert resolve_after.json()["found"] is False


def test_bind_requires_verified_phone() -> None:
    first = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    assert first.json()["verified"] is False
    verification_id = first.json()["verification_id"]

    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-002"},
    )
    assert bind_resp.status_code == 422


def test_verify_phone_sets_verified_at_on_success() -> None:
    first = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    assert first.status_code == 200
    assert first.json()["verified"] is False
    assert first.json()["verified_at"] is None

    second = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    assert second.status_code == 200
    assert second.json()["verified"] is True
    assert second.json()["verified_at"] is not None


def test_unbind_records_unbound_at_and_reason() -> None:
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-audit"},
    )
    alias_id = bind_resp.json()["alias_id"]

    unbind_resp = client.post(
        f"/v1/aliases/{alias_id}/unbind",
        json={"reason_code": "compliance-hold"},
    )
    assert unbind_resp.status_code == 200
    body = unbind_resp.json()
    assert body["status"] == "UNBOUND"
    assert body["unbound_at"] is not None
    assert body["unbound_reason"] == "compliance-hold"


def test_update_discoverable_toggles_bound_alias() -> None:
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-disc", "discoverable": True},
    )
    alias_id = bind_resp.json()["alias_id"]
    assert bind_resp.json()["discoverable"] is True

    off_resp = client.patch(
        f"/v1/aliases/{alias_id}/discoverable",
        json={"discoverable": False},
    )
    assert off_resp.status_code == 200
    assert off_resp.json()["discoverable"] is False
    assert off_resp.json()["status"] == "BOUND"

    on_resp = client.patch(
        f"/v1/aliases/{alias_id}/discoverable",
        json={"discoverable": True},
    )
    assert on_resp.status_code == 200
    assert on_resp.json()["discoverable"] is True


def test_update_discoverable_returns_404_for_unknown_alias() -> None:
    resp = client.patch(
        "/v1/aliases/nonexistent-id/discoverable",
        json={"discoverable": False},
    )
    assert resp.status_code == 404


def test_update_discoverable_returns_409_for_unbound_alias() -> None:
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-409"},
    )
    alias_id = bind_resp.json()["alias_id"]
    client.post(f"/v1/aliases/{alias_id}/unbind", json={"reason_code": "test"})

    resp = client.patch(
        f"/v1/aliases/{alias_id}/discoverable",
        json={"discoverable": False},
    )
    assert resp.status_code == 409


def test_bind_after_unbind_same_user_has_no_recycled_fields() -> None:
    # Same user rebinds their own number — not a recycled-number event
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-same"},
    )
    alias_id = bind_resp.json()["alias_id"]
    client.post(f"/v1/aliases/{alias_id}/unbind", json={"reason_code": "user-request"})

    # Re-verify the phone for a new bind
    client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    verify2 = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    verification_id2 = verify2.json()["verification_id"]

    rebind = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id2, "user_id": "u-same"},
    )
    assert rebind.status_code == 201
    body = rebind.json()
    assert body["recycled_from_user_id"] is None
    assert body["recycled_at"] is None


def test_bind_after_unbind_different_user_records_recycled_info() -> None:
    # Different user binds after prior user unbinds — recycled-number event
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-original"},
    )
    alias_id = bind_resp.json()["alias_id"]
    client.post(f"/v1/aliases/{alias_id}/unbind", json={"reason_code": "number-change"})

    # New user verifies and binds the recycled number
    client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    verify2 = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    verification_id2 = verify2.json()["verification_id"]

    rebind = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id2, "user_id": "u-new"},
    )
    assert rebind.status_code == 201
    body = rebind.json()
    assert body["recycled_from_user_id"] == "u-original"
    assert body["recycled_at"] is not None
    assert body["status"] == "BOUND"
    assert body["user_id"] == "u-new"


def test_alias_history_returns_all_bindings_in_order() -> None:
    # Bind, unbind, rebind (different user) — history should contain 2 entries in order
    verification_id = _do_two_step_verify()
    first_bind = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-hist-a"},
    )
    alias_id = first_bind.json()["alias_id"]
    client.post(f"/v1/aliases/{alias_id}/unbind", json={"reason_code": "test"})

    client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    verify2 = client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    second_bind = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verify2.json()["verification_id"], "user_id": "u-hist-b"},
    )
    assert second_bind.status_code == 201

    hist = client.get(f"/v1/aliases/history/{PHONE}")
    assert hist.status_code == 200
    body = hist.json()
    assert body["phone_e164"] == PHONE
    assert body["total"] == 2
    assert body["aliases"][0]["user_id"] == "u-hist-a"
    assert body["aliases"][0]["status"] == "UNBOUND"
    assert body["aliases"][1]["user_id"] == "u-hist-b"
    assert body["aliases"][1]["status"] == "BOUND"


def test_alias_history_returns_empty_for_unknown_phone() -> None:
    hist = client.get("/v1/aliases/history/+19990000000")
    assert hist.status_code == 200
    body = hist.json()
    assert body["total"] == 0
    assert body["aliases"] == []


def test_alias_history_single_binding() -> None:
    verification_id = _do_two_step_verify()
    client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-single"},
    )
    hist = client.get(f"/v1/aliases/history/{PHONE}")
    assert hist.status_code == 200
    body = hist.json()
    assert body["total"] == 1
    assert body["aliases"][0]["status"] == "BOUND"
    assert body["aliases"][0]["user_id"] == "u-single"


def test_get_alias_by_id_returns_alias() -> None:
    verification_id = _do_two_step_verify()
    bind_resp = client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-direct"},
    )
    alias_id = bind_resp.json()["alias_id"]

    resp = client.get(f"/v1/aliases/{alias_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["alias_id"] == alias_id
    assert body["user_id"] == "u-direct"
    assert body["status"] == "BOUND"


def test_get_alias_by_id_returns_404_for_unknown() -> None:
    resp = client.get("/v1/aliases/does-not-exist")
    assert resp.status_code == 404


def test_resolve_creates_audit_entry_with_caller_id() -> None:
    verification_id = _do_two_step_verify()
    client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-audit-resolve"},
    )

    # Perform two resolves: one found, one not found
    client.get("/v1/aliases/resolve", params={"phone_e164": PHONE}, headers={"X-Caller-Id": "svc-orchestrator"})
    client.get("/v1/aliases/resolve", params={"phone_e164": "+19990000000"}, headers={"X-Caller-Id": "svc-orchestrator"})

    audit = client.get("/v1/aliases/audit/resolve", params={"phone_e164": PHONE})
    assert audit.status_code == 200
    body = audit.json()
    assert body["phone_e164"] == PHONE
    assert body["total"] == 1
    entry = body["entries"][0]
    assert entry["result_found"] is True
    assert entry["caller_id"] == "svc-orchestrator"


def test_resolve_audit_not_found_lookup_recorded() -> None:
    client.get("/v1/aliases/resolve", params={"phone_e164": "+19990000001"})

    audit = client.get("/v1/aliases/audit/resolve", params={"phone_e164": "+19990000001"})
    assert audit.status_code == 200
    body = audit.json()
    assert body["total"] == 1
    assert body["entries"][0]["result_found"] is False
    assert body["entries"][0]["caller_id"] == "anonymous"


def test_resolve_audit_limit_param() -> None:
    verification_id = _do_two_step_verify()
    client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-limit"},
    )
    for _ in range(5):
        client.get("/v1/aliases/resolve", params={"phone_e164": PHONE})

    audit = client.get("/v1/aliases/audit/resolve", params={"phone_e164": PHONE, "limit": 3})
    assert audit.status_code == 200
    body = audit.json()
    assert body["total"] == 3


def test_resolve_allows_three_not_found_lookups_before_throttling() -> None:
    for _ in range(3):
        resp = client.get(
            "/v1/aliases/resolve",
            params={"phone_e164": "+19990000999"},
            headers={"X-Caller-Id": "svc-enumerator"},
        )
        assert resp.status_code == 200
        assert resp.json()["found"] is False


def test_resolve_throttles_fourth_not_found_lookup_for_same_caller() -> None:
    for _ in range(3):
        client.get(
            "/v1/aliases/resolve",
            params={"phone_e164": "+19990000888"},
            headers={"X-Caller-Id": "svc-blocked"},
        )

    blocked = client.get(
        "/v1/aliases/resolve",
        params={"phone_e164": "+19990000889"},
        headers={"X-Caller-Id": "svc-blocked"},
    )
    assert blocked.status_code == 429


def test_resolve_throttles_anonymous_caller_after_three_failures() -> None:
    for _ in range(3):
        client.get("/v1/aliases/resolve", params={"phone_e164": "+19990000777"})

    blocked = client.get("/v1/aliases/resolve", params={"phone_e164": "+19990000778"})
    assert blocked.status_code == 429


def test_successful_resolve_does_not_count_toward_failure_limit() -> None:
    verification_id = _do_two_step_verify()
    client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-safe"},
    )
    for _ in range(3):
        ok = client.get(
            "/v1/aliases/resolve",
            params={"phone_e164": PHONE},
            headers={"X-Caller-Id": "svc-safe"},
        )
        assert ok.status_code == 200
        assert ok.json()["found"] is True

    miss = client.get(
        "/v1/aliases/resolve",
        params={"phone_e164": "+19990000779"},
        headers={"X-Caller-Id": "svc-safe"},
    )
    assert miss.status_code == 200
    assert miss.json()["found"] is False


def test_resolve_audit_summary_counts_found_not_found_and_blocked() -> None:
    verification_id = _do_two_step_verify()
    client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "u-summary"},
    )
    client.get(
        "/v1/aliases/resolve",
        params={"phone_e164": PHONE},
        headers={"X-Caller-Id": "svc-summary"},
    )
    for _ in range(3):
        client.get(
            "/v1/aliases/resolve",
            params={"phone_e164": "+19990000666"},
            headers={"X-Caller-Id": "svc-summary"},
        )
    client.get(
        "/v1/aliases/resolve",
        params={"phone_e164": "+19990000667"},
        headers={"X-Caller-Id": "svc-summary"},
    )

    summary = client.get(
        "/v1/aliases/audit/resolve/summary",
        params={"caller_id": "svc-summary"},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["caller_id"] == "svc-summary"
    assert body["total"] == 5
    assert body["found"] == 1
    assert body["not_found"] == 3
    assert body["blocked"] == 1
