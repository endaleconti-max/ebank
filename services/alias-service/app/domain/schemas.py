import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class VerifyPhoneRequest(BaseModel):
    phone_e164: str
    otp_code: str

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("phone_e164 must be in E.164 format")
        return v

    @field_validator("otp_code")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not (4 <= len(v) <= 6):
            raise ValueError("otp_code must be 4–6 characters")
        return v


class VerifyPhoneResponse(BaseModel):
    verification_id: str
    phone_e164: str
    verified: bool
    verified_at: Optional[datetime] = None


class BindAliasRequest(BaseModel):
    verification_id: str
    user_id: str
    discoverable: bool = True


class AliasResponse(BaseModel):
    alias_id: str
    phone_e164: str
    user_id: str
    discoverable: bool
    status: str
    created_at: datetime
    updated_at: datetime
    unbound_at: Optional[datetime] = None
    unbound_reason: Optional[str] = None
    recycled_from_user_id: Optional[str] = None
    recycled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AliasHistoryResponse(BaseModel):
    phone_e164: str
    status: Optional[str] = None
    total: int
    aliases: List[AliasResponse]


class RecycledAliasListResponse(BaseModel):
    user_id: Optional[str] = None
    total: int
    aliases: List[AliasResponse]


class UndiscoverableAliasListResponse(BaseModel):
    user_id: Optional[str] = None
    total: int
    aliases: List[AliasResponse]


class ResolveAuditEntry(BaseModel):
    log_id: str
    phone_e164: str
    caller_id: Optional[str] = None
    result_found: bool
    blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResolveAuditResponse(BaseModel):
    phone_e164: Optional[str] = None
    caller_id: Optional[str] = None
    window_minutes: Optional[int] = None
    total: int
    entries: List[ResolveAuditEntry]


class ResolveAuditSummaryResponse(BaseModel):
    caller_id: str
    total: int
    found: int
    not_found: int
    blocked: int


class ResolveCallerAuditSummaryEntry(BaseModel):
    caller_id: str
    total: int
    found: int
    not_found: int
    blocked: int
    latest_at: Optional[datetime] = None


class ResolveCallerAuditSummaryListResponse(BaseModel):
    total_callers: int
    window_minutes: int
    callers: List[ResolveCallerAuditSummaryEntry]


class UnbindAliasRequest(BaseModel):
    reason_code: str


class UpdateDiscoverableRequest(BaseModel):
    discoverable: bool


class ResolveAliasResponse(BaseModel):
    found: bool
    alias: Optional[AliasResponse] = None
