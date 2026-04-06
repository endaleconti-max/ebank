import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class AccountType(str, enum.Enum):
    USER_AVAILABLE = "USER_AVAILABLE"
    USER_PENDING = "USER_PENDING"
    TREASURY = "TREASURY"
    FEES_REVENUE = "FEES_REVENUE"
    CONNECTOR_SETTLEMENT = "CONNECTOR_SETTLEMENT"
    DISPUTE_HOLD = "DISPUTE_HOLD"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"


class EntryType(str, enum.Enum):
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"


class PostingDirection(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    account_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status"), default=AccountStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    entry_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_ref: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    transfer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_type: Mapped[EntryType] = mapped_column(Enum(EntryType, name="entry_type"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class JournalPosting(Base):
    __tablename__ = "journal_postings"
    __table_args__ = (
        UniqueConstraint("entry_id", "account_id", "direction", "amount_minor", name="uq_entry_posting"),
    )

    posting_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("journal_entries.entry_id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("ledger_accounts.account_id"), nullable=False)
    direction: Mapped[PostingDirection] = mapped_column(
        Enum(PostingDirection, name="posting_direction"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
