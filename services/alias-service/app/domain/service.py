from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.errors import (
    AliasAlreadyBoundError,
    AliasMustBeBoundError,
    AliasNotFoundError,
    PhoneNotVerifiedError,
    VerificationNotFoundError,
)
from app.domain.models import Alias, AliasStatus, PhoneVerification, ResolveAuditLog
from app.domain.schemas import BindAliasRequest, UnbindAliasRequest, UpdateDiscoverableRequest, VerifyPhoneRequest


class AliasService:
    def verify_phone(self, db: Session, req: VerifyPhoneRequest) -> PhoneVerification:
        existing = (
            db.query(PhoneVerification)
            .filter(PhoneVerification.phone_e164 == req.phone_e164)
            .first()
        )
        if existing is None:
            record = PhoneVerification(
                phone_e164=req.phone_e164,
                otp_code=req.otp_code,
                verified=False,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        if existing.otp_code == req.otp_code:
            if not existing.verified:
                existing.verified = True
                existing.verified_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
        return existing

    def bind_alias(self, db: Session, req: BindAliasRequest) -> Alias:
        verification = (
            db.query(PhoneVerification)
            .filter(PhoneVerification.verification_id == req.verification_id)
            .first()
        )
        if verification is None:
            raise VerificationNotFoundError(req.verification_id)
        if not verification.verified:
            raise PhoneNotVerifiedError(verification.verification_id)

        bound = (
            db.query(Alias)
            .filter(
                Alias.phone_e164 == verification.phone_e164,
                Alias.status == AliasStatus.BOUND,
            )
            .first()
        )
        if bound is not None:
            raise AliasAlreadyBoundError(verification.phone_e164)

        # Detect recycled number: prior UNBOUND binding to a different user
        recycled_from_user_id: Optional[str] = None
        recycled_at: Optional[datetime] = None
        prior = (
            db.query(Alias)
            .filter(
                Alias.phone_e164 == verification.phone_e164,
                Alias.status == AliasStatus.UNBOUND,
            )
            .order_by(Alias.created_at.desc())
            .first()
        )
        if prior is not None and prior.user_id != req.user_id:
            recycled_from_user_id = prior.user_id
            recycled_at = datetime.now(timezone.utc)

        alias = Alias(
            phone_e164=verification.phone_e164,
            user_id=req.user_id,
            discoverable=req.discoverable,
            status=AliasStatus.BOUND,
            recycled_from_user_id=recycled_from_user_id,
            recycled_at=recycled_at,
        )
        db.add(alias)
        db.commit()
        db.refresh(alias)
        return alias

    def unbind_alias(self, db: Session, alias_id: str, req: UnbindAliasRequest) -> Alias:
        alias = db.query(Alias).filter(Alias.alias_id == alias_id).first()
        if alias is None:
            raise AliasNotFoundError(alias_id)
        alias.status = AliasStatus.UNBOUND
        alias.unbound_at = datetime.now(timezone.utc)
        alias.unbound_reason = req.reason_code
        alias.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alias)
        return alias

    def update_discoverable(self, db: Session, alias_id: str, req: UpdateDiscoverableRequest) -> Alias:
        alias = db.query(Alias).filter(Alias.alias_id == alias_id).first()
        if alias is None:
            raise AliasNotFoundError(alias_id)
        if alias.status != AliasStatus.BOUND:
            raise AliasMustBeBoundError(alias_id)
        alias.discoverable = req.discoverable
        alias.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alias)
        return alias

    def resolve_alias(self, db: Session, phone_e164: str, caller_id: Optional[str] = None) -> Optional[Alias]:
        alias = (
            db.query(Alias)
            .filter(
                Alias.phone_e164 == phone_e164,
                Alias.status == AliasStatus.BOUND,
            )
            .first()
        )
        log_entry = ResolveAuditLog(
            phone_e164=phone_e164,
            caller_id=caller_id,
            result_found=alias is not None,
        )
        db.add(log_entry)
        db.commit()
        return alias

    def get_alias_by_id(self, db: Session, alias_id: str) -> Optional[Alias]:
        return db.query(Alias).filter(Alias.alias_id == alias_id).first()

    def get_resolve_audit(self, db: Session, phone_e164: str, limit: int = 100) -> List[ResolveAuditLog]:
        return (
            db.query(ResolveAuditLog)
            .filter(ResolveAuditLog.phone_e164 == phone_e164)
            .order_by(ResolveAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_alias_history(self, db: Session, phone_e164: str) -> List[Alias]:
        return (
            db.query(Alias)
            .filter(Alias.phone_e164 == phone_e164)
            .order_by(Alias.created_at)
            .all()
        )
