from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.domain import service as svc
from app.domain.models import get_db
from app.domain.schemas import (
    CreateRuleRequest,
    EvaluateRequest,
    EvaluateResponse,
    EvaluationLogResponse,
    RuleListResponse,
    RuleResponse,
)

router = APIRouter(prefix="/v1/risk", tags=["risk"])


@router.post("/evaluate", response_model=EvaluateResponse, status_code=200)
def evaluate(payload: EvaluateRequest, request: Request, db: Session = Depends(get_db)):
    caller_id = request.headers.get("X-Caller-Id")
    decision, reason, risk_score, applied_rule_id = svc.evaluate_transfer(
        db,
        sender_user_id=payload.sender_user_id,
        recipient_phone_e164=payload.recipient_phone_e164,
        amount_minor=payload.amount_minor,
        note=payload.note,
        caller_id=caller_id,
    )
    return EvaluateResponse(
        decision=decision,
        reason=reason,
        risk_score=risk_score,
        applied_rule_id=applied_rule_id,
    )


@router.get("/rules", response_model=RuleListResponse)
def list_rules(enabled_only: bool = False, db: Session = Depends(get_db)):
    rules = svc.list_rules(db, enabled_only=enabled_only)
    return RuleListResponse(
        total=len(rules),
        rules=[
            RuleResponse(
                rule_id=r.rule_id,
                name=r.name,
                condition_type=r.condition_type,
                condition_value=r.condition_value,
                action=r.action,
                enabled=r.enabled,
                created_at=r.created_at.isoformat(),
            )
            for r in rules
        ],
    )


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(payload: CreateRuleRequest, db: Session = Depends(get_db)):
    rule = svc.create_rule(
        db,
        name=payload.name,
        condition_type=payload.condition_type,
        condition_value=payload.condition_value,
        action=payload.action,
        enabled=payload.enabled,
    )
    return RuleResponse(
        rule_id=rule.rule_id,
        name=rule.name,
        condition_type=rule.condition_type,
        condition_value=rule.condition_value,
        action=rule.action,
        enabled=rule.enabled,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    deleted = svc.delete_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="rule not found")


@router.get("/log", response_model=EvaluationLogResponse)
def query_log(
    sender_user_id: Optional[str] = None,
    decision: Optional[str] = None,
    window_minutes: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    entries = svc.query_evaluation_log(
        db,
        sender_user_id=sender_user_id,
        decision=decision,
        window_minutes=window_minutes,
        limit=limit,
    )
    from app.domain.schemas import EvaluationLogEntry
    return EvaluationLogResponse(
        total=len(entries),
        sender_user_id=sender_user_id,
        decision=decision,
        window_minutes=window_minutes,
        limit=limit,
        entries=[
            EvaluationLogEntry(
                log_id=e.log_id,
                caller_id=e.caller_id,
                sender_user_id=e.sender_user_id,
                recipient_phone_e164=e.recipient_phone_e164,
                amount_minor=e.amount_minor,
                decision=e.decision,
                reason=e.reason,
                risk_score=e.risk_score,
                applied_rule_id=e.applied_rule_id,
                created_at=e.created_at.isoformat(),
            )
            for e in entries
        ],
    )
