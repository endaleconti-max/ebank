from typing import Optional, Tuple

from app.config import settings
from app.domain.alias_client import resolve_alias
from app.domain.identity_client import get_user_status
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
    # ── 1. Sender KYC / account status check ─────────────────────────────────
    id_result = get_user_status(sender_user_id, caller_id=caller_id)
    if id_result is not None:
        account_status, kyc_status = id_result
        if account_status != "ACTIVE":
            return False, f"sender_account_not_active: {account_status}"
        if kyc_status != "APPROVED":
            return False, f"sender_kyc_not_approved: {kyc_status}"
    else:
        # Service unavailable
        if settings.identity_service_fallback_policy == "deny":
            return False, "identity_service_unavailable: fallback_deny"

    # ── 2. Recipient alias resolution check ──────────────────────────────────
    alias_result = resolve_alias(recipient_phone_e164, caller_id=caller_id)
    if alias_result is not None:
        user_id, alias_id = alias_result
        if not user_id:
            return False, "recipient_alias_not_found"
    else:
        # Service unavailable
        if settings.alias_service_fallback_policy == "deny":
            return False, "alias_service_unavailable: fallback_deny"

    # ── 3. Remote risk-service (first-match-wins rules) ───────────────────────
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
        return True, None  # allow or review

    # ── 4. Local fallback checks ──────────────────────────────────────────────
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
