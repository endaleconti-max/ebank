from typing import List, Optional

from pydantic import BaseModel, field_validator

VALID_CONDITION_TYPES = {"amount_gt", "sender_prefix", "recipient_prefix", "note_keyword"}
VALID_ACTIONS = {"deny", "review"}


class CreateRuleRequest(BaseModel):
    name: str
    condition_type: str
    condition_value: str
    action: str = "deny"
    enabled: bool = True

    @field_validator("condition_type")
    @classmethod
    def validate_condition_type(cls, v: str) -> str:
        if v not in VALID_CONDITION_TYPES:
            raise ValueError(f"condition_type must be one of {sorted(VALID_CONDITION_TYPES)}")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {sorted(VALID_ACTIONS)}")
        return v

    @field_validator("condition_value")
    @classmethod
    def validate_condition_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("condition_value must not be empty")
        return v.strip()


class RuleResponse(BaseModel):
    rule_id: str
    name: str
    condition_type: str
    condition_value: str
    action: str
    enabled: bool
    created_at: str


class RuleListResponse(BaseModel):
    total: int
    rules: List[RuleResponse]


class EvaluateRequest(BaseModel):
    sender_user_id: str
    recipient_phone_e164: str
    amount_minor: int
    note: Optional[str] = None

    @field_validator("amount_minor")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_minor must be positive")
        return v


class EvaluateResponse(BaseModel):
    decision: str          # allow | deny | review
    reason: Optional[str]
    risk_score: int
    applied_rule_id: Optional[str]


class EvaluationLogEntry(BaseModel):
    log_id: str
    caller_id: Optional[str]
    sender_user_id: str
    recipient_phone_e164: str
    amount_minor: int
    decision: str
    reason: Optional[str]
    risk_score: int
    applied_rule_id: Optional[str]
    created_at: str


class EvaluationLogResponse(BaseModel):
    total: int
    sender_user_id: Optional[str]
    decision: Optional[str]
    window_minutes: Optional[int]
    limit: int
    entries: List[EvaluationLogEntry]
