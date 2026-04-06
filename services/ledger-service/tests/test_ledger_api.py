import pytest
from fastapi.testclient import TestClient

from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_account(owner: str) -> str:
    resp = client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": owner,
            "account_type": "USER_AVAILABLE",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201
    return resp.json()["account_id"]


def test_create_balanced_entry_and_compute_balances() -> None:
    account_a = _create_account("u-1")
    account_b = _create_account("u-2")

    post_resp = client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "ext-1001",
            "transfer_id": "t-1001",
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": account_a,
                    "direction": "DEBIT",
                    "amount_minor": 1500,
                    "currency": "USD",
                },
                {
                    "account_id": account_b,
                    "direction": "CREDIT",
                    "amount_minor": 1500,
                    "currency": "USD",
                },
            ],
        },
    )
    assert post_resp.status_code == 201
    entry_id = post_resp.json()["entry_id"]

    entry_resp = client.get(f"/v1/ledger/entries/{entry_id}")
    assert entry_resp.status_code == 200
    assert len(entry_resp.json()["postings"]) == 2

    balance_a = client.get(f"/v1/ledger/accounts/{account_a}/balance")
    balance_b = client.get(f"/v1/ledger/accounts/{account_b}/balance")

    assert balance_a.status_code == 200
    assert balance_b.status_code == 200
    assert balance_a.json()["balance_minor"] == -1500
    assert balance_b.json()["balance_minor"] == 1500


def test_unbalanced_entry_is_rejected() -> None:
    account_a = _create_account("u-3")
    account_b = _create_account("u-4")

    post_resp = client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "ext-2001",
            "transfer_id": "t-2001",
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": account_a,
                    "direction": "DEBIT",
                    "amount_minor": 1500,
                    "currency": "USD",
                },
                {
                    "account_id": account_b,
                    "direction": "CREDIT",
                    "amount_minor": 1400,
                    "currency": "USD",
                },
            ],
        },
    )

    assert post_resp.status_code == 409
    assert "unbalanced" in post_resp.json()["detail"]


def test_reverse_entry_creates_compensating_postings() -> None:
    account_a = _create_account("u-5")
    account_b = _create_account("u-6")

    post_resp = client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "ext-3001",
            "transfer_id": "t-3001",
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": account_a,
                    "direction": "DEBIT",
                    "amount_minor": 700,
                    "currency": "USD",
                },
                {
                    "account_id": account_b,
                    "direction": "CREDIT",
                    "amount_minor": 700,
                    "currency": "USD",
                },
            ],
        },
    )
    assert post_resp.status_code == 201
    original_entry_id = post_resp.json()["entry_id"]

    reverse_resp = client.post(
        f"/v1/ledger/reversals/{original_entry_id}",
        json={"reversal_external_ref": "ext-3001-rev"},
    )
    assert reverse_resp.status_code == 200
    assert reverse_resp.json()["entry_type"] == "REVERSAL"

    balance_a = client.get(f"/v1/ledger/accounts/{account_a}/balance")
    balance_b = client.get(f"/v1/ledger/accounts/{account_b}/balance")

    assert balance_a.json()["balance_minor"] == 0
    assert balance_b.json()["balance_minor"] == 0


def test_list_entry_summaries_export() -> None:
    account_a = _create_account("u-7")
    account_b = _create_account("u-8")

    post_resp = client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": "ext-4001",
            "transfer_id": "t-4001",
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": account_a,
                    "direction": "DEBIT",
                    "amount_minor": 321,
                    "currency": "USD",
                },
                {
                    "account_id": account_b,
                    "direction": "CREDIT",
                    "amount_minor": 321,
                    "currency": "USD",
                },
            ],
        },
    )
    assert post_resp.status_code == 201

    list_resp = client.get("/v1/ledger/entries")
    assert list_resp.status_code == 200
    assert any(
        item["external_ref"] == "ext-4001"
        and item["amount_minor"] == 321
        and item["currency"] == "USD"
        for item in list_resp.json()
    )
