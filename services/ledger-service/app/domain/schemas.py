from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import AccountStatus, AccountType, EntryType, PostingDirection


class CreateAccountRequest(BaseModel):
    owner_type: str = Field(min_length=3, max_length=20)
    owner_id: str = Field(min_length=1, max_length=64)
    account_type: AccountType
    currency: str = Field(min_length=3, max_length=3)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    owner_type: str
    owner_id: str
    account_type: AccountType
    currency: str
    status: AccountStatus
    created_at: datetime


class PostingLineRequest(BaseModel):
    account_id: str
    direction: PostingDirection
    amount_minor: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)


class CreatePostingRequest(BaseModel):
    external_ref: str = Field(min_length=4, max_length=100)
    transfer_id: str = Field(min_length=1, max_length=64)
    entry_type: EntryType
    postings: List[PostingLineRequest] = Field(min_length=2)


class PostingLineResponse(BaseModel):
    posting_id: str
    account_id: str
    direction: PostingDirection
    amount_minor: int
    currency: str


class EntryResponse(BaseModel):
    entry_id: str
    external_ref: str
    transfer_id: str
    entry_type: EntryType
    created_at: datetime
    postings: List[PostingLineResponse]


class EntrySummaryResponse(BaseModel):
    external_ref: str
    amount_minor: int
    currency: str


class BalanceResponse(BaseModel):
    account_id: str
    currency: str
    balance_minor: int


class ReverseEntryRequest(BaseModel):
    reversal_external_ref: str = Field(min_length=4, max_length=100)
