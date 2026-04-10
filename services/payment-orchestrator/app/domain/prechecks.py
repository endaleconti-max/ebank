from typing import Optional, Tuple

from app.config import settings
from app.domain.risk_client import call_risk_service


def run_risk_precheck(amount_minor: int, note: Optional[str]) -> Tuple[bool, Optional[str]]:
    if amount_minor > settings.risk_amount_limit_minor:
        return False, "risk_precheck_failed: amount exceeds configured limit"
    if note and "fraud" in note.lower():
        return False, "risk_precheck_failed: note flagged by rule"
    return True, None


def run_compliance_precheck(sender_user_id: str, recipient_phone_e164: str) -> Tuple[bool, Optional[str]]:
    if sender_user_id.startswith("blocked-"):
        return False, "compliance_precheck_failed: sender is blocked"
    if recipient_phone_e164.startswith("+999"):
        return False, "compliance_precheck_failed: recipient geography blocked"
    return True, None


def run_prechecks(
    sender_user_id: str,
    recipient_phone_e164: str,
    amount_minor: int,
    note: Optional[str],
    caller_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    # Attempt remote risk-service first; fall back to local checks on failure.
    result = call_risk_service(
        sender_user_id=sender_user_id,
        recipient_phone_e164=recipient_phone_e164,
        amount_minor=amount_minor,
        note=note,
        caller_id=caller_id,
    )
    if result is not None:
        decision, reason = result
        if decision == "deny":
            return False, f"risk_service_denied: {reason}"
        if decision == "review":
            # review means pass validation but surface the reason
            return True, None
        return True, None  # allow

    # Local fallback
    risk_ok, risk_reason = run_risk_precheck(amount_minor=amount_minor, note=note)
    if not risk_ok:
        return False, risk_reason

    compliance_ok, compliance_reason = run_compliance_precheck(
        sender_user_id=sender_user_id,
        recipient_phone_e164=recipient_phone_e164,
    )
    if not compliance_ok:
        return False, compliance_reason

    return True, None
