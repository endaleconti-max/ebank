import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class RunStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MismatchType(str, enum.Enum):
    MISSING_CONNECTOR_TRANSACTION = "MISSING_CONNECTOR_TRANSACTION"
    ORPHAN_CONNECTOR_TRANSACTION = "ORPHAN_CONNECTOR_TRANSACTION"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    CONNECTOR_FAILED = "CONNECTOR_FAILED"


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="recon_run_status"), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mismatch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReconciliationMismatch(Base):
    __tablename__ = "reconciliation_mismatches"

    mismatch_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("reconciliation_runs.run_id"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    mismatch_type: Mapped[MismatchType] = mapped_column(Enum(MismatchType, name="mismatch_type"), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
