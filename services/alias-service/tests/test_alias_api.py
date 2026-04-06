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
