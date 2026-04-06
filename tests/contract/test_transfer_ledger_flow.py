"""
Contract: payment-orchestrator → ledger-service

Validates that:
  1. A transfer created in the orchestrator can drive ledger account postings.
  2. The transfer_id issued by the orchestrator is accepted as the ledger
     entry's transfer_id (cross-service field compatibility).
  3. The orchestrator state machine advances correctly from CREATED → SETTLED.
  4. Ledger balances reflect the DEBIT/CREDIT postings for the transfer amount.
  5. A ledger reversal correctly negates the original entry.
  6. Duplicate transfers are idempotent (same Idempotency-Key → same transfer_id).
"""

CURRENCY = "USD"
AMOUNT = 2500


def _create_ledger_account(ledger_client, owner_id: str, account_type: str) -> str:
    resp = ledger_client.post(
        "/v1/ledger/accounts",
        json={
            "owner_type": "USER",
            "owner_id": owner_id,
            "account_type": account_type,
            "currency": CURRENCY,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["account_id"]


def test_transfer_drives_ledger_double_entry_and_settles(
    orchestrator_client, ledger_client
) -> None:
    # ── ledger-service: create sender + receiver accounts ─────────────────
    sender_acct = _create_ledger_account(ledger_client, "user-sender-1", "USER_AVAILABLE")
    receiver_acct = _create_ledger_account(ledger_client, "user-receiver-1", "USER_AVAILABLE")

    # ── orchestrator: create transfer ─────────────────────────────────────
    transfer_resp = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "user-sender-1",
            "recipient_phone_e164": "+15550005555",
            "currency": CURRENCY,
            "amount_minor": AMOUNT,
            "note": "contract test",
        },
        headers={"Idempotency-Key": "contract-txfr-001"},
    )
    assert transfer_resp.status_code == 201
    transfer_id = transfer_resp.json()["transfer_id"]
    assert transfer_resp.json()["status"] == "CREATED"

    # Idempotency: second request with same key returns same transfer
    dup = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "user-sender-1",
            "recipient_phone_e164": "+15550005555",
            "currency": CURRENCY,
            "amount_minor": AMOUNT,
        },
        headers={"Idempotency-Key": "contract-txfr-001"},
    )
    assert dup.status_code == 201
    assert dup.json()["transfer_id"] == transfer_id

    # ── orchestrator: advance through state machine ────────────────────────
    for next_status in ("VALIDATED", "RESERVED"):
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": next_status}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status

    # ── ledger-service: post double-entry using transfer_id from orchestrator
    entry_resp = ledger_client.post(
        "/v1/ledger/postings",
        json={
            "external_ref": f"transfer-{transfer_id}",
            "transfer_id": transfer_id,          # cross-service field
            "entry_type": "TRANSFER",
            "postings": [
                {
                    "account_id": sender_acct,
                    "direction": "DEBIT",
                    "amount_minor": AMOUNT,
                    "currency": CURRENCY,
                },
                {
                    "account_id": receiver_acct,
                    "direction": "CREDIT",
                    "amount_minor": AMOUNT,
                    "currency": CURRENCY,
                },
            ],
        },
    )
    assert entry_resp.status_code == 201
    entry_id = entry_resp.json()["entry_id"]
    assert entry_resp.json()["transfer_id"] == transfer_id

    # ── ledger-service: verify balances ───────────────────────────────────
    sender_bal = ledger_client.get(f"/v1/ledger/accounts/{sender_acct}/balance")
    receiver_bal = ledger_client.get(f"/v1/ledger/accounts/{receiver_acct}/balance")
    assert sender_bal.json()["balance_minor"] == -AMOUNT
    assert receiver_bal.json()["balance_minor"] == AMOUNT

    # ── orchestrator: advance to SUBMITTED_TO_RAIL then SETTLED ───────────
    for next_status in ("SUBMITTED_TO_RAIL", "SETTLED"):
        resp = orchestrator_client.post(
            f"/v1/transfers/{transfer_id}/transition", json={"status": next_status}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status

    events_resp = orchestrator_client.get(f"/v1/transfers/{transfer_id}/events")
    assert events_resp.status_code == 200
    assert any(item["event_type"] == "TRANSFER_CREATED" for item in events_resp.json())
    assert any(item["to_status"] == "SETTLED" for item in events_resp.json())

    first_relay = orchestrator_client.post("/v1/transfers/events/relay")
    assert first_relay.status_code == 200
    assert first_relay.json()["exported_count"] >= 1

    second_relay = orchestrator_client.post("/v1/transfers/events/relay")
    assert second_relay.status_code == 200
    assert second_relay.json()["exported_count"] == 0

    # ── ledger-service: reverse entry → balances return to zero ───────────
    reversal_resp = ledger_client.post(
        f"/v1/ledger/reversals/{entry_id}",
        json={"reversal_external_ref": f"reversal-{transfer_id}"},
    )
    assert reversal_resp.status_code == 200
    # Reversal flips every posting direction; net balances should return to 0
    sender_bal_after = ledger_client.get(f"/v1/ledger/accounts/{sender_acct}/balance")
    receiver_bal_after = ledger_client.get(f"/v1/ledger/accounts/{receiver_acct}/balance")
    assert sender_bal_after.json()["balance_minor"] == 0
    assert receiver_bal_after.json()["balance_minor"] == 0


def test_invalid_state_transition_is_rejected(orchestrator_client) -> None:
    resp = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-x",
            "recipient_phone_e164": "+15550007777",
            "currency": "USD",
            "amount_minor": 100,
        },
        headers={"Idempotency-Key": "contract-txfr-002"},
    )
    assert resp.status_code == 201
    transfer_id = resp.json()["transfer_id"]

    # Cannot jump CREATED → SETTLED (must go through VALIDATED → RESERVED → …)
    invalid = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SETTLED"}
    )
    assert invalid.status_code == 409
