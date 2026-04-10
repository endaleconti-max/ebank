from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.models import AccountStatus, KycStatus


class CreateUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=140)
    country_code: str = Field(min_length=2, max_length=2)
    email: EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    full_name: str
    country_code: str
    email: EmailStr
    account_status: AccountStatus
    kyc_status: KycStatus
    created_at: datetime
    updated_at: datetime


class KycSubmissionRequest(BaseModel):
    provider_case_id: str = Field(min_length=3, max_length=64)


class KycDecisionRequest(BaseModel):
    decision: KycStatus


class UserStatusResponse(BaseModel):
    user_id: str
    account_status: AccountStatus
    kyc_status: KycStatus


class AccountStatusChangeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=256)


class AccountAuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str
    user_id: str
    from_status: str
    to_status: str
    reason: str
    actor_id: str
    created_at: datetime
