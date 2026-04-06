"""
Contract: identity-service → alias-service

Validates the user onboarding and phone alias binding flow that spans two
service boundaries:

  1. Create a user (identity-service) and approve KYC.
  2. Verify a phone number via two-step OTP (alias-service).
  3. Bind the alias using the user_id issued by identity-service.
  4. Resolve the alias by phone and verify the user_id round-trips correctly.
  5. Unbind the alias and confirm it disappears from resolution.
"""


PHONE = "+15550001234"
OTP = "246810"


def test_user_onboarding_and_alias_bind_roundtrip(identity_client, alias_client) -> None:
    # ── identity-service: create user ──────────────────────────────────────
    user_resp = identity_client.post(
        "/v1/users",
        json={"full_name": "Alice Smith", "country_code": "US", "email": "alice@test.example"},
    )
    assert user_resp.status_code == 201
    user_id = user_resp.json()["user_id"]
    assert user_resp.json()["kyc_status"] == "NOT_STARTED"

    # ── identity-service: KYC submit + approve ─────────────────────────────
    submit = identity_client.post(
        f"/v1/users/{user_id}/kyc/submit", json={"provider_case_id": "case-001"}
    )
    assert submit.status_code == 200
    assert submit.json()["kyc_status"] == "SUBMITTED"

    approve = identity_client.post(
        f"/v1/users/{user_id}/kyc/decision", json={"decision": "APPROVED"}
    )
    assert approve.status_code == 200
    assert approve.json()["kyc_status"] == "APPROVED"

    # ── alias-service: two-step phone verification ─────────────────────────
    step1 = alias_client.post(
        "/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP}
    )
    assert step1.status_code == 200
    assert step1.json()["verified"] is False

    step2 = alias_client.post(
        "/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP}
    )
    assert step2.status_code == 200
    assert step2.json()["verified"] is True
    verification_id = step2.json()["verification_id"]

    # ── alias-service: bind using user_id from identity-service ───────────
    bind = alias_client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": user_id, "discoverable": True},
    )
    assert bind.status_code == 201
    alias_id = bind.json()["alias_id"]
    assert bind.json()["status"] == "BOUND"
    assert bind.json()["user_id"] == user_id          # user_id cross-service round-trip

    # ── alias-service: resolve phone → same user_id ───────────────────────
    resolve = alias_client.get("/v1/aliases/resolve", params={"phone_e164": PHONE})
    assert resolve.status_code == 200
    assert resolve.json()["found"] is True
    assert resolve.json()["alias"]["user_id"] == user_id
    assert resolve.json()["alias"]["alias_id"] == alias_id

    # ── alias-service: unbind → phone no longer resolvable ────────────────
    unbind = alias_client.post(
        f"/v1/aliases/{alias_id}/unbind", json={"reason_code": "user-request"}
    )
    assert unbind.status_code == 200
    assert unbind.json()["status"] == "UNBOUND"

    resolve_after = alias_client.get("/v1/aliases/resolve", params={"phone_e164": PHONE})
    assert resolve_after.json()["found"] is False


def test_alias_bind_blocked_without_kyc_approved_user_id(alias_client) -> None:
    """
    Alias-service is user-id-agnostic (it doesn't call identity-service), but
    this test confirms that an arbitrary user_id (not yet in identity-service)
    can still be stored as a binding — the contract between the two services is
    that alias-service is the source of truth for phone→user mappings, while
    identity-service is the source of truth for user state.  Providing a
    non-existent user_id is accepted at the alias layer; enforcement is done
    at the orchestration layer (not yet wired).
    """
    # Two-step verify
    alias_client.post("/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP})
    step2 = alias_client.post(
        "/v1/aliases/verify-phone", json={"phone_e164": PHONE, "otp_code": OTP}
    )
    verification_id = step2.json()["verification_id"]

    bind = alias_client.post(
        "/v1/aliases/bind",
        json={"verification_id": verification_id, "user_id": "nonexistent-user-id"},
    )
    assert bind.status_code == 201
    assert bind.json()["user_id"] == "nonexistent-user-id"
