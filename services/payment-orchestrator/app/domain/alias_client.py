"""
HTTP client for the alias-service.

Calls GET /v1/aliases/resolve?phone_e164=... to verify the recipient phone
has an active, discoverable alias.
Returns (user_id, alias_id) on success (alias found), ("", "") on not-found
(404 or decision=not_found), or None on any connection/timeout error.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import urlopen as _urlopen
from typing import Optional, Tuple

from app.config import settings

_logger = logging.getLogger(__name__)


def resolve_alias(
    phone_e164: str,
    caller_id: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """
    Resolve a recipient phone number to (user_id, alias_id).

    Returns:
      (user_id, alias_id) when a discoverable BOUND alias exists
      ("", "")           when the alias is not found (safe not-found signal)
      None               when the service is unavailable (caller applies fallback)
    """
    if not settings.alias_service_enabled:
        return None

    params = urllib.parse.urlencode({"phone_e164": phone_e164})
    url = f"{settings.alias_service_base_url}/v1/aliases/resolve?{params}"
    req = urllib.request.Request(
        url,
        headers={
            **({"X-Caller-Id": caller_id} if caller_id else {}),
        },
        method="GET",
    )

    try:
        with _urlopen(req, timeout=settings.alias_service_timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            user_id = body.get("user_id") or ""
            alias_id = body.get("alias_id") or ""
            return user_id, alias_id
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "", ""  # known not-found — recipient phone is unregistered
        _logger.warning("alias-service HTTP error %s, applying fallback", exc.code)
        return None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _logger.warning("alias-service unavailable, applying fallback: %s", exc)
        return None
