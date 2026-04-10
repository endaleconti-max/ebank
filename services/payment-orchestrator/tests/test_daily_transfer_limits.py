"""Tests for daily transfer limit enforcement by KYC tier."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import Base, Transfer, TransferStatus
from app.domain.prechecks import check_daily_transfer_limits


# In-memory SQLite for testing
engine = create_engine("sqlite:///:memory:", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def insert_transfer(
    db: Session,
    sender_user_id: str,
    amount_minor: int,
    status: TransferStatus = TransferStatus.SETTLED,
    hours_ago: int = 0,
) -> Transfer:
    """Helper to insert a transfer for testing."""
    now_utc = datetime.now(timezone.utc)
    created_at = now_utc - timedelta(hours=hours_ago)

    transfer = Transfer(
        idempotency_key=f"test-key-{sender_user_id}-{amount_minor}-{hours_ago}",
        sender_user_id=sender_user_id,
        recipient_phone_e164="+15005550100",
        currency="USD",
        amount_minor=amount_minor,
        status=status,
        created_at=created_at,
    )
    db.add(transfer)
    db.commit()
    return transfer


def test_daily_limit_approved_tier_single_transfer_under_limit():
    """APPROVED tier (2M daily): single transfer at 100k should pass."""
    db = SessionLocal()

    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-1",
        kyc_status="APPROVED",
        amount_minor=100_000,
    )

    db.close()
    assert ok is True
    assert reason is None


def test_daily_limit_approved_tier_accumulates_today():
    """APPROVED tier (2M daily): multiple transfers today should accumulate against daily limit."""
    db = SessionLocal()

    # Insert 1.5M transfer 2 hours ago
    insert_transfer(db, "u-approved-2", 1_500_000, TransferStatus.SETTLED, hours_ago=2)

    # Try to add 600k more (would total 2.1M, exceeds 2M daily limit)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-2",
        kyc_status="APPROVED",
        amount_minor=600_000,
    )

    db.close()
    assert ok is False
    assert "daily_transfer_limit_exceeded" in reason
    assert "2100000" in reason  # projected total
    assert "2000000" in reason  # limit


def test_daily_limit_approved_tier_exactly_at_limit_passes():
    """APPROVED tier (2M daily): transfer bringing total exactly to daily limit should pass."""
    db = SessionLocal()

    # Insert 1.2M transfer 1 hour ago
    insert_transfer(db, "u-approved-3", 1_200_000, TransferStatus.SETTLED, hours_ago=1)

    # Try to add 800k more (total = 2M, exactly at limit)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-3",
        kyc_status="APPROVED",
        amount_minor=800_000,
    )

    db.close()
    assert ok is True
    assert reason is None


def test_daily_limit_not_started_tier_capped_at_20k():
    """NOT_STARTED tier (20k daily): transfer at 15k today should pass."""
    db = SessionLocal()

    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-not-started-1",
        kyc_status="NOT_STARTED",
        amount_minor=15_000,
    )

    db.close()
    assert ok is True
    assert reason is None


def test_daily_limit_not_started_tier_exceeds_daily():
    """NOT_STARTED tier (20k daily): transfer exceeding 20k daily limit should fail."""
    db = SessionLocal()

    # Insert 15k transfer 3 hours ago
    insert_transfer(db, "u-not-started-2", 15_000, TransferStatus.SETTLED, hours_ago=3)

    # Try to add 10k more (would total 25k, exceeds 20k daily limit)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-not-started-2",
        kyc_status="NOT_STARTED",
        amount_minor=10_000,
    )

    db.close()
    assert ok is False
    assert "daily_transfer_limit_exceeded" in reason
    assert "25000" in reason  # projected total


def test_daily_limit_rejected_tier_blocks_all():
    """REJECTED tier (0 daily): any transfer should be blocked."""
    db = SessionLocal()

    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-rejected-1",
        kyc_status="REJECTED",
        amount_minor=1,  # even 1 minor unit should be blocked
    )

    db.close()
    assert ok is False
    assert "daily_transfer_limit_exceeded" in reason


def test_daily_limit_only_counts_successful_statuses():
    """Daily limit should only count SETTLED, VALIDATED, RESERVED; not FAILED or REVERSED."""
    db = SessionLocal()

    # Insert 450k SETTLED
    insert_transfer(db, "u-approved-4", 450_000, TransferStatus.SETTLED, hours_ago=2)

    # Insert 100k FAILED (should not count)
    insert_transfer(db, "u-approved-4", 100_000, TransferStatus.FAILED, hours_ago=1)

    # Insert 50k REVERSED (should not count)
    insert_transfer(db, "u-approved-4", 50_000, TransferStatus.REVERSED, hours_ago=0)

    # Try to add 100k (should check against only SETTLED 450k, so 450k + 100k = 550k, over limit)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-4",
        kyc_status="APPROVED",
        amount_minor=100_000,
    )

    db.close()
    assert ok is False
    assert "550000" in reason  # should be 450 + 100, not 450 + 100 + 100 + 50


def test_daily_limit_sunset_at_midnight_utc():
    """Transfers created before today (UTC) should not count toward today's limit."""
    db = SessionLocal()

    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)
    yesterday_transfer = Transfer(
        idempotency_key="yesterday-1",
        sender_user_id="u-approved-5",
        recipient_phone_e164="+15005550100",
        currency="USD",
        amount_minor=400_000,
        status=TransferStatus.SETTLED,
        created_at=yesterday_utc.replace(hour=23, minute=59),  # end of yesterday
    )
    db.add(yesterday_transfer)
    db.commit()

    # Try to add 400k (should only check against today's transfers, which is 0)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-5",
        kyc_status="APPROVED",
        amount_minor=400_000,
    )

    db.close()
    assert ok is True  # 0 (yesterday doesn't count) + 400k < 500k daily


def test_daily_limit_disabled_globally():
    """When transfer_limits_enabled=False, daily limit check should pass."""
    from unittest.mock import patch

    db = SessionLocal()

    # Insert 400k transfer
    insert_transfer(db, "u-approved-6", 400_000, TransferStatus.SETTLED, hours_ago=1)

    # Try to add 200k with limits disabled
    with patch("app.domain.prechecks.settings.transfer_limits_enabled", False):
        ok, reason = check_daily_transfer_limits(
            db=db,
            sender_user_id="u-approved-6",
            kyc_status="APPROVED",
            amount_minor=200_000,
        )

    db.close()
    assert ok is True
    assert reason is None


def test_daily_limit_with_no_db_session():
    """When db=None, daily limit check should pass (defensive)."""
    ok, reason = check_daily_transfer_limits(
        db=None,
        sender_user_id="u-any",
        kyc_status="APPROVED",
        amount_minor=1_000_000,  # way over any limit
    )

    assert ok is True
    assert reason is None


def test_daily_limit_submitted_tier_same_as_not_started():
    """SUBMITTED tier should have same daily limit as NOT_STARTED (20k)."""
    db = SessionLocal()

    # Insert 15k transfer
    insert_transfer(db, "u-submitted-1", 15_000, TransferStatus.SETTLED, hours_ago=2)

    # Try to add 10k (would total 25k, exceeds 20k)
    ok, reason = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-submitted-1",
        kyc_status="SUBMITTED",
        amount_minor=10_000,
    )

    db.close()
    assert ok is False
    assert "daily_transfer_limit_exceeded" in reason
    assert "25000" in reason


def test_daily_limit_integration_approved_multiple_tiers():
    """Multiple users with different tiers should be tracked independently."""
    db = SessionLocal()

    # User 1: APPROVED, 400k today
    insert_transfer(db, "u-approved-7", 400_000, TransferStatus.SETTLED, hours_ago=2)

    # User 2: NOT_STARTED, 15k today
    insert_transfer(db, "u-not-started-3", 15_000, TransferStatus.SETTLED, hours_ago=1)

    # User 1 tries 150k more (550k total, exceeds APPROVED 500k limit)
    ok1, reason1 = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-approved-7",
        kyc_status="APPROVED",
        amount_minor=150_000,
    )

    # User 2 tries 5k more (20k total, at NOT_STARTED 20k limit) -> should pass
    ok2, reason2 = check_daily_transfer_limits(
        db=db,
        sender_user_id="u-not-started-3",
        kyc_status="NOT_STARTED",
        amount_minor=5_000,
    )

    db.close()
    assert ok1 is False
    assert "daily_transfer_limit_exceeded" in reason1
    assert ok2 is True
    assert reason2 is None
