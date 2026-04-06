"""
End-to-end contract: orchestrator submission -> connector callback -> reconciliation.

Flow covered:
1. Create transfer and drive it to SUBMITTED_TO_RAIL.
2. Create matching ledger posting and connector transaction using orchestrator external_ref.
3. Deliver connector callback to orchestrator and ensure transfer settles.
4. Run reconciliation and ensure no mismatch exists for this external_ref.
"""


def _create_ledger_account(ledger_client, owner_id: str, account_type: str) -> str:
    resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": owner_id,
            "account_type": account_type,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201
    return resp.json()["account_id"]


def test_end_to_end_orchestrator_callback_and_reconciliation(
    orchestrator_client, ledger_client, connector_client, recon_client
) -> None:
    # 1) Create and advance transfer to SUBMITTED_TO_RAIL
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-e2e-1",
            "recipient_phone_e164": "+15550101010",
            "currency": "USD",
            "amount_minor": 1200,
            "note": "e2e",
        },
        headers={"Idempotency-Key": "e2e-transfer-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    validated = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"}
    )
    assert validated.status_code == 200

    reserved = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"}
    )
    assert reserved.status_code == 200

    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED_TO_RAIL"
    external_ref = submitted.json()["connector_external_ref"]
    assert external_ref is not None

    # 2) Seed ledger + connector records with same external_ref for reconciliation
    sender_acct = _create_ledger_account(ledger_client, "u-e2e-sender", "USER_AVAILABLE")
    recv_acct = _create_ledger_account(ledger_client, "u-e2e-recv", "USER_AVAILABLE")

    ledger_post = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": external_ref,
            "transfer_id": transfer_id,
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": sender_acct,
                    "direction": "DEBIT",
                    "amount_minor": 1200,
                    "currency": "USD",
                },
                {
                    "account_id": recv_acct,
                    "direction": "CREDIT",
                    "amount_minor": 1200,
                    "currency": "USD",
                },
            ],
        },
    )
    assert ledger_post.status_code == 201

    payout = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 1200,
            "currency": "USD",
            "destination": "acct-e2e-1",
        },
    )
    assert payout.status_code == 201

    # 3) Confirm connector callback into orchestrator
    callback = orchestrator_client.post(
        "/v1/transfers/callbacks/connector",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )
    assert callback.status_code == 200
    assert callback.json()["status"] == "SETTLED"

    events_resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events")
    assert events_resp.status_code == 200
    assert any(
        item["event_type"] == "TRANSFER_CONNECTOR_CALLBACK_CONFIRMED"
        and item["to_status"] == "SETTLED"
        for item in events_resp.json()
    )

    # Keep connector status aligned for reconciliation
    connector_client.post(
        "/v1/connectors/simulate-callback",
        json={"external_ref": external_ref, "status": "CONFIRMED"},
    )

    # 4) Reconcile and ensure this ref has no mismatch
    run = recon_client.post("/v1/reconciliation/runs", json={})
    assert run.status_code == 201
    run_id = run.json()["run"]["run_id"]

    detail = recon_client.get(f"/v1/reconciliation/runs/{run_id}")
    assert detail.status_code == 200

    mismatches_for_ref = [
        m for m in detail.json()["mismatches"] if m["external_ref"] == external_ref
    ]
    assert mismatches_for_ref == []
