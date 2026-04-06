from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import TransferStatus


class CreateTransferRequest(BaseModel):
    sender_user_id: str = Field(min_length=1, max_length=64)
    recipient_phone_e164: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    currency: str = Field(min_length=3, max_length=3)
    amount_minor: int = Field(ge=1)
    note: Optional[str] = Field(default=None, max_length=140)
    sender_ledger_account_id: Optional[str] = Field(default=None, max_length=36)
    transit_ledger_account_id: Optional[str] = Field(default=None, max_length=36)


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transfer_id: str
    idempotency_key: str
    sender_user_id: str
    recipient_phone_e164: str
    recipient_alias_id: Optional[str]
    connector_external_ref: Optional[str]
    currency: str
    amount_minor: int
    note: Optional[str]
    status: TransferStatus
    failure_reason: Optional[str]
    sender_ledger_account_id: Optional[str]
    transit_ledger_account_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class TransitionTransferRequest(BaseModel):
    status: TransferStatus
    failure_reason: Optional[str] = Field(default=None, max_length=240)


class ConnectorCallbackRequest(BaseModel):
    external_ref: str = Field(min_length=4, max_length=120)
    status: str = Field(min_length=4, max_length=24)
    failure_reason: Optional[str] = Field(default=None, max_length=240)


class TransferEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    transfer_id: str
    event_type: str
    from_status: Optional[TransferStatus]
    to_status: Optional[TransferStatus]
    failure_reason: Optional[str]
    created_at: datetime


class TransferEventRelayResponse(BaseModel):
    events: list[TransferEventResponse]
    exported_count: int


class TransferListResponse(BaseModel):
    transfers: list[TransferResponse]
    next_cursor: Optional[str]
    count: int
