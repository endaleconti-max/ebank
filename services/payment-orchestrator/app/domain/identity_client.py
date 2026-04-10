"""
HTTP client for the identity-service.

Calls GET /v1/users/{user_id}/status to verify sender KYC and account status.
Returns (account_status, kyc_status) on success, or None on any connection /
timeout error so the caller can apply its fallback policy.
"""
import json
import logging
import urllib.error
import urllib.request
from urllib.request import urlopen as _urlopen
from typing import Optional, Tuple

from app.config import settings

_logger = logging.getLogger(__name__)


def get_user_status(
    user_id: str,
    caller_id: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """
    Fetch user account_status and kyc_status from identity-service.

    Returns (account_status, kyc_status) or None on any error.
    """
    if not settings.identity_service_enabled:
        return None

    url = f"{settings.identity_service_base_url}/v1/users/{user_id}/status"
    req = urllib.request.Request(
        url,
        headers={
            **({"X-Caller-Id": caller_id} if caller_id else {}),
        },
        method="GET",
    )

    try:
        with _urlopen(req, timeout=settings.identity_service_timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("account_status"), body.get("kyc_status")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        _logger.warning("identity-service unavailable, applying fallback: %s", exc)
        return None
