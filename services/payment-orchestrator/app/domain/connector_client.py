from typing import Dict

import httpx

from app.config import settings
from app.domain.models import Transfer


def submit_payout(transfer: Transfer) -> Dict[str, str]:
    external_ref = f"orchestrator-{transfer.transfer_id}"

    if settings.connector_submission_mode.lower() == "mock":
        return {"ok": "true", "reason": "", "external_ref": external_ref}

    payload = {
        "transfer_id": transfer.transfer_id,
        "external_ref": external_ref,
        "amount_minor": transfer.amount_minor,
        "currency": transfer.currency,
        "destination": settings.connector_destination,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.connector_base_url.rstrip('/')}/v1/connectors/{settings.connector_id}/payouts",
                json=payload,
            )
    except httpx.HTTPError:
        return {"ok": "false", "reason": "connector_unavailable", "external_ref": external_ref}

    if response.status_code >= 500:
        return {"ok": "false", "reason": "connector_unavailable", "external_ref": external_ref}
    if response.status_code >= 400:
        return {"ok": "false", "reason": f"connector_rejected:{response.status_code}", "external_ref": external_ref}

    body = response.json()
    status = body.get("status", "FAILED")
    if status == "FAILED":
        return {"ok": "false", "reason": "connector_status_failed", "external_ref": external_ref}

    return {"ok": "true", "reason": "", "external_ref": external_ref}