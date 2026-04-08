from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.errors import (
    AliasAlreadyBoundError,
    AliasMustBeBoundError,
    AliasNotFoundError,
    PhoneNotVerifiedError,
    ResolveLookupRateLimitedError,
    VerificationNotFoundError,
)
from app.domain.models import Alias, AliasStatus, PhoneVerification, ResolveAuditLog
from app.domain.schemas import BindAliasRequest, UnbindAliasRequest, UpdateDiscoverableRequest, VerifyPhoneRequest


class AliasService:
    RESOLVE_FAILURE_WINDOW_MINUTES = 60
    RESOLVE_FAILURE_LIMIT = 3

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
        return self._resolve_alias(
            db,
            phone_e164,
            caller_id=caller_id,
            include_undiscoverable=False,
            lookup_scope="PUBLIC",
            purpose=None,
        )

    def resolve_alias_internal(
        self,
        db: Session,
        phone_e164: str,
        caller_id: str,
        purpose: str,
        include_undiscoverable: bool = True,
    ) -> Optional[Alias]:
        return self._resolve_alias(
            db,
            phone_e164,
            caller_id=caller_id,
            include_undiscoverable=include_undiscoverable,
            lookup_scope="INTERNAL",
            purpose=purpose,
        )

    def _resolve_alias(
        self,
        db: Session,
        phone_e164: str,
        caller_id: Optional[str],
        include_undiscoverable: bool,
        lookup_scope: str,
        purpose: Optional[str],
    ) -> Optional[Alias]:
        caller_key = caller_id or "anonymous"
        window_start = datetime.now(timezone.utc) - timedelta(minutes=self.RESOLVE_FAILURE_WINDOW_MINUTES)
        recent_failed_count = (
            db.query(ResolveAuditLog)
            .filter(
                ResolveAuditLog.caller_id == caller_key,
                ResolveAuditLog.result_found.is_(False),
                ResolveAuditLog.blocked.is_(False),
                ResolveAuditLog.created_at >= window_start,
            )
            .count()
        )
        if recent_failed_count >= self.RESOLVE_FAILURE_LIMIT:
            db.add(
                ResolveAuditLog(
                    phone_e164=phone_e164,
                    caller_id=caller_key,
                    lookup_scope=lookup_scope,
                    purpose=purpose,
                    result_found=False,
                    blocked=True,
                )
            )
            db.commit()
            raise ResolveLookupRateLimitedError(caller_key)

        query = db.query(Alias).filter(
            Alias.phone_e164 == phone_e164,
            Alias.status == AliasStatus.BOUND,
        )
        if not include_undiscoverable:
            query = query.filter(Alias.discoverable.is_(True))
        alias = query.first()
        log_entry = ResolveAuditLog(
            phone_e164=phone_e164,
            caller_id=caller_key,
            lookup_scope=lookup_scope,
            purpose=purpose,
            result_found=alias is not None,
            blocked=False,
        )
        db.add(log_entry)
        db.commit()
        return alias

    def get_alias_by_id(self, db: Session, alias_id: str) -> Optional[Alias]:
        return db.query(Alias).filter(Alias.alias_id == alias_id).first()

    def get_resolve_audit(self, db: Session, phone_e164: str, limit: int = 100) -> List[ResolveAuditLog]:
        return self.query_resolve_audit(db, phone_e164=phone_e164, limit=limit)

    def query_resolve_audit(
        self,
        db: Session,
        phone_e164: Optional[str] = None,
        caller_id: Optional[str] = None,
        lookup_scope: Optional[str] = None,
        window_minutes: Optional[int] = None,
        limit: int = 100,
    ) -> List[ResolveAuditLog]:
        query = db.query(ResolveAuditLog)
        if phone_e164:
            query = query.filter(ResolveAuditLog.phone_e164 == phone_e164)
        if caller_id:
            query = query.filter(ResolveAuditLog.caller_id == caller_id)
        if lookup_scope:
            query = query.filter(ResolveAuditLog.lookup_scope == lookup_scope)
        if window_minutes is not None:
            window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
            query = query.filter(ResolveAuditLog.created_at >= window_start)
        return query.order_by(ResolveAuditLog.created_at.desc()).limit(limit).all()

    def get_resolve_audit_summary(self, db: Session, caller_id: Optional[str] = None) -> dict:
        caller_key = caller_id or "anonymous"
        entries = (
            db.query(ResolveAuditLog)
            .filter(ResolveAuditLog.caller_id == caller_key)
            .all()
        )
        total = len(entries)
        found = sum(1 for entry in entries if entry.result_found and not entry.blocked)
        blocked = sum(1 for entry in entries if entry.blocked)
        not_found = total - found - blocked
        return {
            "caller_id": caller_key,
            "total": total,
            "found": found,
            "not_found": not_found,
            "blocked": blocked,
        }

    def list_resolve_audit_summaries(
        self,
        db: Session,
        window_minutes: int = 60,
        limit: int = 50,
        blocked_only: bool = False,
    ) -> List[dict]:
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        entries = (
            db.query(ResolveAuditLog)
            .filter(ResolveAuditLog.created_at >= window_start)
            .order_by(ResolveAuditLog.created_at.desc())
            .all()
        )
        by_caller = {}
        for entry in entries:
            caller_key = entry.caller_id or "anonymous"
            stats = by_caller.setdefault(
                caller_key,
                {
                    "caller_id": caller_key,
                    "total": 0,
                    "found": 0,
                    "not_found": 0,
                    "blocked": 0,
                    "latest_at": None,
                },
            )
            stats["total"] += 1
            if entry.blocked:
                stats["blocked"] += 1
            elif entry.result_found:
                stats["found"] += 1
            else:
                stats["not_found"] += 1
            if stats["latest_at"] is None or entry.created_at > stats["latest_at"]:
                stats["latest_at"] = entry.created_at

        summaries = list(by_caller.values())
        if blocked_only:
            summaries = [summary for summary in summaries if summary["blocked"] > 0]
        summaries.sort(
            key=lambda summary: (
                summary["blocked"],
                summary["not_found"],
                summary["total"],
                summary["caller_id"],
            ),
            reverse=True,
        )
        return summaries[:limit]

    def get_alias_history(
        self,
        db: Session,
        phone_e164: str,
        status: Optional[AliasStatus] = None,
    ) -> List[Alias]:
        query = db.query(Alias).filter(Alias.phone_e164 == phone_e164)
        if status is not None:
            query = query.filter(Alias.status == status)
        return query.order_by(Alias.created_at).all()

    def list_recycled_aliases(
        self,
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Alias]:
        query = db.query(Alias).filter(Alias.recycled_at.is_not(None))
        if user_id:
            query = query.filter(Alias.user_id == user_id)
        return query.order_by(Alias.recycled_at.desc()).limit(limit).all()

    def list_undiscoverable_aliases(
        self,
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Alias]:
        query = db.query(Alias).filter(
            Alias.status == AliasStatus.BOUND,
            Alias.discoverable.is_(False),
        )
        if user_id:
            query = query.filter(Alias.user_id == user_id)
        return query.order_by(Alias.updated_at.desc()).limit(limit).all()
