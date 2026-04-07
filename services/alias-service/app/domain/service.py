from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.errors import (
    AliasAlreadyBoundError,
    AliasNotFoundError,
    PhoneNotVerifiedError,
    VerificationNotFoundError,
)
from app.domain.models import Alias, AliasStatus, PhoneVerification
from app.domain.schemas import BindAliasRequest, UnbindAliasRequest, VerifyPhoneRequest


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

        alias = Alias(
            phone_e164=verification.phone_e164,
            user_id=req.user_id,
            discoverable=req.discoverable,
            status=AliasStatus.BOUND,
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
        alias.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alias)
        return alias

    def resolve_alias(self, db: Session, phone_e164: str) -> Optional[Alias]:
        return (
            db.query(Alias)
            .filter(
                Alias.phone_e164 == phone_e164,
                Alias.status == AliasStatus.BOUND,
            )
            .first()
        )
