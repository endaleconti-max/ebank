import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine
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


class RiskRule(Base):
    """A configurable risk evaluation rule."""

    __allow_unmapped__ = True

    __tablename__ = "risk_rules"

    rule_id: str = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: str = mapped_column(String, nullable=False)
    # Condition types:
    #   amount_gt   — deny/review when amount_minor > condition_value (int)
    #   sender_prefix — deny/review when sender_user_id starts with condition_value
    #   recipient_prefix — deny/review when recipient_phone_e164 starts with condition_value
    #   note_keyword — deny/review when note contains condition_value (case-insensitive)
    condition_type: str = mapped_column(String, nullable=False)
    condition_value: str = mapped_column(String, nullable=False)
    # action: "deny" | "review"
    action: str = mapped_column(String, nullable=False, default="deny")
    enabled: bool = mapped_column(Boolean, nullable=False, default=True)
    created_at: datetime = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class RiskEvaluationLog(Base):
    """Immutable log of every risk evaluation call."""

    __allow_unmapped__ = True

    __tablename__ = "risk_evaluation_log"

    log_id: str = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_id: str = mapped_column(String, nullable=True, index=True)
    sender_user_id: str = mapped_column(String, nullable=False, index=True)
    recipient_phone_e164: str = mapped_column(String, nullable=False)
    amount_minor: int = mapped_column(Integer, nullable=False)
    decision: str = mapped_column(String, nullable=False)  # allow | deny | review
    reason: str = mapped_column(Text, nullable=True)
    risk_score: int = mapped_column(Integer, nullable=False, default=0)
    applied_rule_id: str = mapped_column(String, nullable=True)
    created_at: datetime = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


Base.metadata.create_all(bind=engine)
