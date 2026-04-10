import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    __allow_unmapped__ = True


class ScreeningDecision(str, enum.Enum):
    CLEAR = "clear"
    HIT = "hit"
    POTENTIAL_MATCH = "potential_match"


class WatchlistEntry(Base):
    """A sanctions / watchlist record."""

    __allow_unmapped__ = True
    __tablename__ = "watchlist_entries"

    entry_id: str = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Name of the sanctioned individual or entity
    name: str = mapped_column(String, nullable=False, index=True)
    # ISO country code where this entry applies (optional)
    country_code: str = mapped_column(String, nullable=True)
    # Short code describing the list or reason (e.g. "OFAC-SDN", "UN-SANCTIONS")
    reason_code: str = mapped_column(String, nullable=False, default="UNSPECIFIED")
    active: bool = mapped_column(Boolean, nullable=False, default=True)
    added_at: datetime = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ScreeningLog(Base):
    """Immutable audit record of every screening call."""

    __allow_unmapped__ = True
    __tablename__ = "screening_log"

    log_id: str = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Identifier of the entity being screened (user_id, transfer_id, etc.)
    subject_id: str = mapped_column(String, nullable=False, index=True)
    # What kind of subject: "user" | "transfer" | "counterparty"
    subject_type: str = mapped_column(String, nullable=False, default="user")
    # The name that was screened
    name: str = mapped_column(String, nullable=False)
    decision: str = mapped_column(
        Enum(ScreeningDecision, name="screening_decision"),
        nullable=False,
    )
    # Set when decision is HIT or POTENTIAL_MATCH
    matched_entry_id: str = mapped_column(String, nullable=True)
    matched_entry_name: str = mapped_column(String, nullable=True)
    reason_code: str = mapped_column(String, nullable=True)
    caller_id: str = mapped_column(String, nullable=True, index=True)
    screened_at: datetime = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


Base.metadata.create_all(bind=engine)
