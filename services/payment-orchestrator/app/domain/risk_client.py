"""
HTTP client for the standalone risk-service.

Calls POST /v1/risk/evaluate on the configured risk service URL.
Returns (decision, reason) where decision is "allow" | "deny" | "review".

Falls back gracefully to None on any connection or timeout error so the caller
can use local prechecks as a fallback.
"""
import logging
from typing import Optional, Tuple

import urllib.request
import urllib.error
import json

from app.config import settings

_logger = logging.getLogger(__name__)


def call_risk_service(
    *,
    sender_user_id: str,
    recipient_phone_e164: str,
    amount_minor: int,
    note: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> Optional[Tuple[str, Optional[str]]]:
    """
    Call the risk-service evaluate endpoint.

    Returns (decision, reason) on success, or None on any error so the caller
    can fall back to local prechecks.
    """
    if not settings.risk_service_enabled:
        return None

    payload = {
        "sender_user_id": sender_user_id,
        "recipient_phone_e164": recipient_phone_e164,
        "amount_minor": amount_minor,
    }
    if note:
        payload["note"] = note

    url = f"{settings.risk_service_base_url}/v1/risk/evaluate"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **({"X-Caller-Id": caller_id} if caller_id else {}),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.risk_service_timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            decision = body.get("decision", "allow")
            reason = body.get("reason")
            return decision, reason
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        _logger.warning("risk-service unavailable, falling back to local prechecks: %s", exc)
        return None
