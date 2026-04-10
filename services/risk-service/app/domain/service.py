from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.models import RiskEvaluationLog, RiskRule


def _match_rule(rule: RiskRule, *, sender_user_id: str, recipient_phone_e164: str,
                amount_minor: int, note: Optional[str]) -> bool:
    """Return True when the request triggers this rule."""
    ct = rule.condition_type
    cv = rule.condition_value
    if ct == "amount_gt":
        return amount_minor > int(cv)
    if ct == "sender_prefix":
        return sender_user_id.startswith(cv)
    if ct == "recipient_prefix":
        return recipient_phone_e164.startswith(cv)
    if ct == "note_keyword":
        return bool(note) and cv.lower() in note.lower()
    return False


def evaluate_transfer(
    db: Session,
    *,
    sender_user_id: str,
    recipient_phone_e164: str,
    amount_minor: int,
    note: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> Tuple[str, Optional[str], int, Optional[str]]:
    """
    Evaluate a transfer request against all enabled rules.

    Returns (decision, reason, risk_score, applied_rule_id).
    decision: "allow" | "deny" | "review"
    """
    rules: List[RiskRule] = (
        db.query(RiskRule)
        .filter(RiskRule.enabled == True)  # noqa: E712
        .order_by(RiskRule.created_at.asc())
        .all()
    )

    # Apply rules in creation order — first match wins
    for rule in rules:
        if _match_rule(
            rule,
            sender_user_id=sender_user_id,
            recipient_phone_e164=recipient_phone_e164,
            amount_minor=amount_minor,
            note=note,
        ):
            decision = rule.action  # "deny" or "review"
            reason = f"rule:{rule.rule_id}:{rule.name}"
            risk_score = 100 if decision == "deny" else 50
            _log(
                db,
                caller_id=caller_id,
                sender_user_id=sender_user_id,
                recipient_phone_e164=recipient_phone_e164,
                amount_minor=amount_minor,
                decision=decision,
                reason=reason,
                risk_score=risk_score,
                applied_rule_id=rule.rule_id,
            )
            return decision, reason, risk_score, rule.rule_id

    # Fallback: default amount limit check
    if amount_minor > settings.default_amount_limit_minor:
        reason = "default_limit_exceeded"
        _log(
            db,
            caller_id=caller_id,
            sender_user_id=sender_user_id,
            recipient_phone_e164=recipient_phone_e164,
            amount_minor=amount_minor,
            decision="deny",
            reason=reason,
            risk_score=100,
            applied_rule_id=None,
        )
        return "deny", reason, 100, None

    _log(
        db,
        caller_id=caller_id,
        sender_user_id=sender_user_id,
        recipient_phone_e164=recipient_phone_e164,
        amount_minor=amount_minor,
        decision="allow",
        reason=None,
        risk_score=0,
        applied_rule_id=None,
    )
    return "allow", None, 0, None


def _log(
    db: Session,
    *,
    caller_id: Optional[str],
    sender_user_id: str,
    recipient_phone_e164: str,
    amount_minor: int,
    decision: str,
    reason: Optional[str],
    risk_score: int,
    applied_rule_id: Optional[str],
) -> None:
    entry = RiskEvaluationLog(
        caller_id=caller_id,
        sender_user_id=sender_user_id,
        recipient_phone_e164=recipient_phone_e164,
        amount_minor=amount_minor,
        decision=decision,
        reason=reason,
        risk_score=risk_score,
        applied_rule_id=applied_rule_id,
    )
    db.add(entry)
    db.commit()


# ── Rule CRUD ─────────────────────────────────────────────────────────────────

def create_rule(
    db: Session,
    *,
    name: str,
    condition_type: str,
    condition_value: str,
    action: str,
    enabled: bool,
) -> RiskRule:
    rule = RiskRule(
        name=name,
        condition_type=condition_type,
        condition_value=condition_value,
        action=action,
        enabled=enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session, *, enabled_only: bool = False) -> List[RiskRule]:
    q = db.query(RiskRule)
    if enabled_only:
        q = q.filter(RiskRule.enabled == True)  # noqa: E712
    return q.order_by(RiskRule.created_at.asc()).all()


def delete_rule(db: Session, rule_id: str) -> bool:
    rule = db.get(RiskRule, rule_id)
    if rule is None:
        return False
    db.delete(rule)
    db.commit()
    return True


# ── Evaluation log query ──────────────────────────────────────────────────────

def query_evaluation_log(
    db: Session,
    *,
    sender_user_id: Optional[str] = None,
    decision: Optional[str] = None,
    window_minutes: Optional[int] = None,
    limit: int = 100,
) -> List[RiskEvaluationLog]:
    q = db.query(RiskEvaluationLog)
    if sender_user_id:
        q = q.filter(RiskEvaluationLog.sender_user_id == sender_user_id)
    if decision:
        q = q.filter(RiskEvaluationLog.decision == decision)
    if window_minutes is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        q = q.filter(RiskEvaluationLog.created_at >= cutoff)
    return q.order_by(RiskEvaluationLog.created_at.desc()).limit(limit).all()
