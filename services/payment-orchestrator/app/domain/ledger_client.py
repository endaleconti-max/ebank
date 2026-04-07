"""HTTP client helpers for posting transfer journal entries to ledger-service.

Called by the orchestrator when transitions require balance movement:
- RESERVED -> SUBMITTED_TO_RAIL: debit sender and credit transit
- SETTLED -> REVERSED: debit transit and credit sender
"""
from typing import Dict

import httpx

from app.config import settings
from app.domain.models import Transfer


def post_transfer_entry(transfer: Transfer) -> Dict[str, str]:
    """Post the double-entry for a payout submission.

    Returns a dict with key "ok": "true" | "false" and optionally "entry_id".
    Never raises — a failed ledger posting is logged and surfaced via the return
    value so the caller can decide whether to treat it as fatal.
    """
    if not (transfer.sender_ledger_account_id and transfer.transit_ledger_account_id):
        return {"ok": "skipped", "reason": "ledger_account_ids_not_set"}

    external_ref = f"payout-{transfer.transfer_id}"
    payload = {
        "external_ref": external_ref,
        "transfer_id": transfer.transfer_id,
        "entry_type": "TRANSFER",
        "postings": [
            {
                "account_id": transfer.sender_ledger_account_id,
                "direction": "DEBIT",
                "amount_minor": transfer.amount_minor,
                "currency": transfer.currency,
            },
            {
                "account_id": transfer.transit_ledger_account_id,
                "direction": "CREDIT",
                "amount_minor": transfer.amount_minor,
                "currency": transfer.currency,
            },
        ],
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{settings.ledger_base_url.rstrip('/')}/v1/ledger/postings",
                json=payload,
            )
    except httpx.HTTPError:
        return {"ok": "false", "reason": "ledger_unavailable"}

    if response.status_code in {200, 201}:
        return {"ok": "true", "entry_id": response.json().get("entry_id", "")}
    if response.status_code == 409:
        # Idempotent duplicate — treat as success.
        return {"ok": "true", "reason": "duplicate_accepted"}
    return {"ok": "false", "reason": f"ledger_error:{response.status_code}"}


def post_reversal_entry(transfer: Transfer) -> Dict[str, str]:
    """Post the double-entry that reverses a settled transfer.

    Debits the transit account and credits the sender account for the original
    transfer amount, recorded as a REVERSAL journal entry for clearer audit
    semantics.
    """
    if not (transfer.sender_ledger_account_id and transfer.transit_ledger_account_id):
        return {"ok": "skipped", "reason": "ledger_account_ids_not_set"}

    external_ref = f"reversal-{transfer.transfer_id}"
    payload = {
        "external_ref": external_ref,
        "transfer_id": transfer.transfer_id,
        "entry_type": "REVERSAL",
        "postings": [
            {
                "account_id": transfer.transit_ledger_account_id,
                "direction": "DEBIT",
                "amount_minor": transfer.amount_minor,
                "currency": transfer.currency,
            },
            {
                "account_id": transfer.sender_ledger_account_id,
                "direction": "CREDIT",
                "amount_minor": transfer.amount_minor,
                "currency": transfer.currency,
            },
        ],
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{settings.ledger_base_url.rstrip('/')}/v1/ledger/postings",
                json=payload,
            )
    except httpx.HTTPError:
        return {"ok": "false", "reason": "ledger_unavailable"}

    if response.status_code in {200, 201}:
        return {"ok": "true", "entry_id": response.json().get("entry_id", "")}
    if response.status_code == 409:
        return {"ok": "true", "reason": "duplicate_accepted"}
    return {"ok": "false", "reason": f"ledger_error:{response.status_code}"}
