import pytest
from fastapi.testclient import TestClient

from app.api.routes import IDEMPOTENCY_CACHE
from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    IDEMPOTENCY_CACHE.clear()


def test_create_user_and_get_status_flow() -> None:
    create_resp = client.post(
        "/v1/users",
        json={
            "full_name": "Jane Doe",
            "country_code": "US",
            "email": "jane@example.com",
        },
        headers={"Idempotency-Key": "idem-user-1"},
    )
    assert create_resp.status_code == 201

    body = create_resp.json()
    user_id = body["user_id"]
    assert body["kyc_status"] == "NOT_STARTED"

    status_resp = client.get(f"/v1/users/{user_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["account_status"] == "ACTIVE"

    submit_resp = client.post(
        f"/v1/users/{user_id}/kyc/submit",
        json={"provider_case_id": "case-001"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["kyc_status"] == "SUBMITTED"

    decision_resp = client.post(
        f"/v1/users/{user_id}/kyc/decision",
        json={"decision": "APPROVED"},
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["kyc_status"] == "APPROVED"


def test_idempotent_create_user_returns_same_user() -> None:
    payload = {
        "full_name": "John Smith",
        "country_code": "GB",
        "email": "john@example.com",
    }

    first = client.post("/v1/users", json=payload, headers={"Idempotency-Key": "idem-user-2"})
    second = client.post("/v1/users", json=payload, headers={"Idempotency-Key": "idem-user-2"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["user_id"] == second.json()["user_id"]
