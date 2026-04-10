"""
HTTP client for the compliance-service sanctions screening endpoint.

Calls POST /v1/compliance/screen on the configured compliance service URL.
Returns (decision, matched_entry_id, matched_entry_name) on success, or None
on any connection / timeout error so the caller can proceed with the fallback
policy defined in identity-service config.
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Optional, Tuple

from app.config import settings

_logger = logging.getLogger(__name__)


def screen_subject(
    *,
    subject_id: str,
    subject_type: str,
    name: str,
    caller_id: Optional[str] = None,
) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """
    Call the compliance-service screen endpoint.

    Returns (decision, matched_entry_id, matched_entry_name) on success,
    or None on any error so the caller can apply its fallback policy.
    decision: "clear" | "hit" | "potential_match"
    """
    if not settings.compliance_service_enabled:
        return None

    payload = {
        "subject_id": subject_id,
        "subject_type": subject_type,
        "name": name,
    }
    url = f"{settings.compliance_service_base_url}/v1/compliance/screen"
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
        with urllib.request.urlopen(req, timeout=settings.compliance_service_timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return (
                body.get("decision", "clear"),
                body.get("matched_entry_id"),
                body.get("matched_entry_name"),
            )
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        _logger.warning(
            "compliance-service unavailable, applying fallback policy: %s", exc
        )
        return None
