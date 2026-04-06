import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class TransferStatus(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    RESERVED = "RESERVED"
    SUBMITTED_TO_RAIL = "SUBMITTED_TO_RAIL"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class Transfer(Base):
    __tablename__ = "transfers"

    transfer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sender_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_alias_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    connector_external_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"), default=TransferStatus.CREATED, nullable=False
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )


class TransferEvent(Base):
    __tablename__ = "transfer_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transfer_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[Optional[TransferStatus]] = mapped_column(
        Enum(TransferStatus, name="transfer_status_event_from"), nullable=True
    )
    to_status: Mapped[Optional[TransferStatus]] = mapped_column(
        Enum(TransferStatus, name="transfer_status_event_to"), nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    relayed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
