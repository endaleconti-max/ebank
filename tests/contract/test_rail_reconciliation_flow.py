"""
Contract: connector-gateway → reconciliation-service

Validates that:
  1. A ledger entry and a matching connector payout for the same external_ref
     produce zero reconciliation mismatches.
  2. A ledger entry with NO matching connector transaction is flagged as
     MISSING_CONNECTOR_TRANSACTION.
  3. A connector transaction with NO matching ledger entry is flagged as
     ORPHAN_CONNECTOR_TRANSACTION.
  4. An amount discrepancy between ledger and connector is flagged as
     AMOUNT_MISMATCH.

The reconciliation-service reads the ledger and connector DBs directly via
raw sqlite3, so the contract test uses file-based SQLite (configured in
conftest.py) to ensure cross-service reads work correctly.
"""

CURRENCY = "USD"


def _post_ledger_entry(ledger_client, external_ref: str, transfer_id: str, amount: int) -> str:
    """Create two accounts and post a balanced double-entry.  Returns entry_id."""
    debit_acct = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": f"treasury-{transfer_id}",
            "account_type": "TREASURY",
            "currency": CURRENCY,
        },
    ).json()["account_id"]

    credit_acct = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "SYSTEM",
            "owner_id": f"settlement-{transfer_id}",
            "account_type": "CONNECTOR_SETTLEMENT",
            "currency": CURRENCY,
        },
    ).json()["account_id"]

    resp = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": external_ref,
            "transfer_id": transfer_id,
            "entry_type": "TRANSFER",
            "postings": [
                {"account_id": debit_acct, "direction": "DEBIT", "amount_minor": amount, "currency": CURRENCY},
                {"account_id": credit_acct, "direction": "CREDIT", "amount_minor": amount, "currency": CURRENCY},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["entry_id"]


def _submit_and_confirm_payout(connector_client, external_ref: str, transfer_id: str, amount: int) -> None:
    """Submit a payout to mock-bank-a and simulate a CONFIRMED callback."""
    payout = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": amount,
            "currency": CURRENCY,
            "destination": "acct-dest-001",
        },
    )
    assert payout.status_code == 201, payout.text
    assert payout.json()["status"] == "PENDING"

    callback = connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert callback.json()["accepted"] is True


def test_matched_ledger_and_connector_entry_has_no_mismatches(
    ledger_client, connector_client, recon_client
) -> None:
    EXT_REF = "ext-match-001"
    TRANSFER_ID = "t-match-001"
    AMOUNT = 5000

    _post_ledger_entry(ledger_client, EXT_REF, TRANSFER_ID, AMOUNT)
    _submit_and_confirm_payout(connector_client, EXT_REF, TRANSFER_ID, AMOUNT)

    run = recon_client.post("/v1/reconciliation/runs", json={})
    assert run.status_code == 201
    run_id = run.json()["run"]["run_id"]

    detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["run"]["status"] == "COMPLETED"
    assert detail.json()["run"]["matched_count"] == 1

    mismatches_for_ref = [
        m for m in detail.json()["mismatches"] if m["external_ref"] == EXT_REF
    ]
    assert mismatches_for_ref == [], f"Unexpected mismatches: {mismatches_for_ref}"


def test_missing_connector_entry_flagged(ledger_client, recon_client) -> None:
    EXT_REF = "ext-ledger-only-001"
    AMOUNT = 1000

    _post_ledger_entry(ledger_client, EXT_REF, "t-ledger-only-001", AMOUNT)
    # No connector payout is submitted

    run = recon_client.post("/v1/reconciliation/runs", json={})
    assert run.status_code == 201
    run_id = run.json()["run"]["run_id"]

    detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
    mismatch_types = {m["mismatch_type"] for m in detail.json()["mismatches"]}
    assert "MISSING_CONNECTOR_TRANSACTION" in mismatch_types


def test_orphan_connector_entry_flagged(connector_client, recon_client) -> None:
    EXT_REF = "ext-connector-only-001"
    AMOUNT = 750
    # Submit a payout but post NO ledger entry
    _submit_and_confirm_payout(connector_client, EXT_REF, "t-connector-only-001", AMOUNT)

    run = recon_client.post("/v1/reconciliation/runs", json={})
    assert run.status_code == 201
    run_id = run.json()["run"]["run_id"]

    detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
    mismatch_types = {m["mismatch_type"] for m in detail.json()["mismatches"]}
    assert "ORPHAN_CONNECTOR_TRANSACTION" in mismatch_types


def test_amount_mismatch_between_ledger_and_connector(
    ledger_client, connector_client, recon_client
) -> None:
    EXT_REF = "ext-amount-mismatch-001"
    TRANSFER_ID = "t-amount-mismatch-001"
    LEDGER_AMOUNT = 2000
    CONNECTOR_AMOUNT = 1999  # one cent off

    _post_ledger_entry(ledger_client, EXT_REF, TRANSFER_ID, LEDGER_AMOUNT)
    _submit_and_confirm_payout(connector_client, EXT_REF, TRANSFER_ID, CONNECTOR_AMOUNT)

    run = recon_client.post("/v1/reconciliation/runs", json={})
    assert run.status_code == 201
    run_id = run.json()["run"]["run_id"]

    detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
    mismatch_types = {m["mismatch_type"] for m in detail.json()["mismatches"]}
    assert "AMOUNT_MISMATCH" in mismatch_types
