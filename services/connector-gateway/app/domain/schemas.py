from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ConnectorStatus, RailOperation


class ExecuteRailRequest(BaseModel):
    transfer_id: str = Field(min_length=1, max_length=64)
    external_ref: str = Field(min_length=4, max_length=120)
    amount_minor: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=64)


class ConnectorTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connector_txn_id: str
    connector_id: str
    operation: RailOperation
    transfer_id: str
    external_ref: str
    amount_minor: int
    currency: str
    destination: str
    status: ConnectorStatus
    provider_response_code: Optional[str]
    provider_response_body: Optional[str]
    created_at: datetime
    updated_at: datetime


class ConnectorTransactionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    connector_txn_id: str
    external_ref: str
    transfer_id: str
    connector_id: str
    amount_minor: int
    currency: str
    status: ConnectorStatus
    event_type: str
    created_at: datetime


class ConnectorWebhookRequest(BaseModel):
    external_ref: str = Field(min_length=4, max_length=120)
    status: ConnectorStatus
    provider_response_code: Optional[str] = Field(default=None, max_length=32)
    provider_response_body: Optional[str] = Field(default=None, max_length=1000)


class SimulateCallbackRequest(BaseModel):
    external_ref: str = Field(min_length=4, max_length=120)
    status: ConnectorStatus


class SimulateCallbackResponse(BaseModel):
    accepted: bool
    transaction: Optional[ConnectorTransactionResponse] = None
