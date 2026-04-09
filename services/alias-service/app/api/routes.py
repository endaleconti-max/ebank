from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.domain.errors import (
    AliasAlreadyBoundError,
    AliasMustBeBoundError,
    AliasNotFoundError,
    PhoneNotVerifiedError,
    ResolveLookupRateLimitedError,
    VerificationNotFoundError,
)
from app.domain.schemas import (
    AliasHistoryResponse,
    LifecycleAuditSummaryResponse,
    RecycledAliasListResponse,
    AliasResponse,
    BindAliasRequest,
    DiscoverabilityAuditResponse,
    DiscoverabilityReasonSummaryListResponse,
    DiscoverabilityUserSummaryListResponse,
    ResolvePurposeAuditSummaryListResponse,
    ResolveAliasResponse,
    ResolveCallerAuditSummaryListResponse,
    ResolveAuditResponse,
    ResolveAuditSummaryResponse,
    UnbindAuditResponse,
    UnbindReasonSummaryListResponse,
    UnbindUserSummaryListResponse,
    UndiscoverableAliasListResponse,
    UnbindAliasRequest,
    UpdateDiscoverableRequest,
    VerifyPhoneRequest,
    VerifyPhoneResponse,
)
from app.domain.service import AliasService
from app.domain.models import AliasStatus
from app.infrastructure.db import get_db

router = APIRouter()
_svc = AliasService()


@router.post("/v1/aliases/verify-phone", response_model=VerifyPhoneResponse)
def verify_phone(payload: VerifyPhoneRequest, db: Session = Depends(get_db)):
    record = _svc.verify_phone(db, payload)
    return VerifyPhoneResponse(
        verification_id=record.verification_id,
        phone_e164=record.phone_e164,
        verified=record.verified,
        verified_at=record.verified_at,
    )


@router.post("/v1/aliases/bind", status_code=201, response_model=AliasResponse)
def bind_alias(payload: BindAliasRequest, db: Session = Depends(get_db)):
    try:
        alias = _svc.bind_alias(db, payload)
    except VerificationNotFoundError:
        raise HTTPException(status_code=404, detail="Verification not found")
    except PhoneNotVerifiedError:
        raise HTTPException(status_code=422, detail="Phone not verified")
    except AliasAlreadyBoundError:
        raise HTTPException(status_code=409, detail="Alias already bound for this phone")
    return alias


@router.post("/v1/aliases/{alias_id}/unbind", response_model=AliasResponse)
def unbind_alias(alias_id: str, payload: UnbindAliasRequest, db: Session = Depends(get_db)):
    try:
        alias = _svc.unbind_alias(db, alias_id, payload)
    except AliasNotFoundError:
        raise HTTPException(status_code=404, detail="Alias not found")
    return alias


@router.patch("/v1/aliases/{alias_id}/discoverable", response_model=AliasResponse)
def update_discoverable(alias_id: str, payload: UpdateDiscoverableRequest, db: Session = Depends(get_db)):
    try:
        alias = _svc.update_discoverable(db, alias_id, payload)
    except AliasNotFoundError:
        raise HTTPException(status_code=404, detail="Alias not found")
    except AliasMustBeBoundError:
        raise HTTPException(status_code=409, detail="Alias must be BOUND to update discoverability")
    return alias


@router.get("/v1/aliases/resolve", response_model=ResolveAliasResponse)
def resolve_alias(request: Request, phone_e164: str, db: Session = Depends(get_db)):
    caller_id = request.headers.get("X-Caller-Id")
    try:
        alias = _svc.resolve_alias(db, phone_e164, caller_id=caller_id)
    except ResolveLookupRateLimitedError:
        raise HTTPException(status_code=429, detail="Resolve lookup rate limit exceeded")
    if alias is None:
        return ResolveAliasResponse(found=False)
    return ResolveAliasResponse(found=True, alias=alias)


@router.get("/v1/aliases/resolve/internal", response_model=ResolveAliasResponse)
def resolve_alias_internal(
    request: Request,
    phone_e164: str,
    purpose: str,
    include_undiscoverable: bool = True,
    db: Session = Depends(get_db),
):
    caller_id = request.headers.get("X-Caller-Id")
    if not caller_id:
        raise HTTPException(status_code=422, detail="X-Caller-Id header is required")
    if purpose not in _svc.INTERNAL_RESOLVE_PURPOSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid internal resolve purpose. Allowed: {', '.join(_svc.INTERNAL_RESOLVE_PURPOSES)}",
        )
    try:
        alias = _svc.resolve_alias_internal(
            db,
            phone_e164,
            caller_id=caller_id,
            purpose=purpose,
            include_undiscoverable=include_undiscoverable,
        )
    except ResolveLookupRateLimitedError:
        raise HTTPException(status_code=429, detail="Resolve lookup rate limit exceeded")
    if alias is None:
        return ResolveAliasResponse(found=False)
    return ResolveAliasResponse(found=True, alias=alias)


@router.get("/v1/aliases/audit/resolve", response_model=ResolveAuditResponse)
def get_resolve_audit(
    phone_e164: Optional[str] = None,
    caller_id: Optional[str] = None,
    lookup_scope: Optional[str] = Query(default=None),
    window_minutes: Optional[int] = Query(default=None, ge=1, le=1440),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if not phone_e164 and not caller_id:
        raise HTTPException(status_code=422, detail="phone_e164 or caller_id is required")
    if lookup_scope is not None and lookup_scope not in {"PUBLIC", "INTERNAL"}:
        raise HTTPException(status_code=422, detail="Invalid lookup scope filter")
    entries = _svc.query_resolve_audit(
        db,
        phone_e164=phone_e164,
        caller_id=caller_id,
        lookup_scope=lookup_scope,
        window_minutes=window_minutes,
        limit=limit,
    )
    return ResolveAuditResponse(
        phone_e164=phone_e164,
        caller_id=caller_id,
        lookup_scope=lookup_scope,
        window_minutes=window_minutes,
        total=len(entries),
        entries=entries,
    )


@router.get("/v1/aliases/audit/resolve/summary", response_model=ResolveAuditSummaryResponse)
def get_resolve_audit_summary(
    caller_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _svc.get_resolve_audit_summary(db, caller_id=caller_id)


@router.get("/v1/aliases/audit/resolve/callers", response_model=ResolveCallerAuditSummaryListResponse)
def list_resolve_audit_callers(
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    blocked_only: bool = False,
    db: Session = Depends(get_db),
):
    callers = _svc.list_resolve_audit_summaries(
        db,
        window_minutes=window_minutes,
        limit=limit,
        blocked_only=blocked_only,
    )
    return ResolveCallerAuditSummaryListResponse(
        total_callers=len(callers),
        window_minutes=window_minutes,
        callers=callers,
    )


@router.get("/v1/aliases/audit/resolve/purposes", response_model=ResolvePurposeAuditSummaryListResponse)
def list_resolve_audit_purposes(
    lookup_scope: str = Query(default="INTERNAL"),
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if lookup_scope not in {"PUBLIC", "INTERNAL"}:
        raise HTTPException(status_code=422, detail="Invalid lookup scope filter")
    purposes = _svc.list_resolve_audit_purpose_summaries(
        db,
        lookup_scope=lookup_scope,
        window_minutes=window_minutes,
        limit=limit,
    )
    return ResolvePurposeAuditSummaryListResponse(
        total_purposes=len(purposes),
        lookup_scope=lookup_scope,
        window_minutes=window_minutes,
        purposes=purposes,
    )


@router.get("/v1/aliases/audit/unbind-reasons", response_model=UnbindReasonSummaryListResponse)
def list_unbind_reason_summaries(
    reason_code: Optional[str] = None,
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    reasons = _svc.list_unbind_reason_summaries(
        db,
        reason_code=reason_code,
        window_minutes=window_minutes,
        limit=limit,
    )
    return UnbindReasonSummaryListResponse(
        reason_code=reason_code,
        total_reasons=len(reasons),
        window_minutes=window_minutes,
        reasons=reasons,
    )


@router.get("/v1/aliases/audit/unbind", response_model=UnbindAuditResponse)
def get_unbind_audit(
    phone_e164: Optional[str] = None,
    user_id: Optional[str] = None,
    reason_code: Optional[str] = None,
    window_minutes: Optional[int] = Query(default=None, ge=1, le=1440),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    entries = _svc.query_unbind_audit(
        db,
        phone_e164=phone_e164,
        user_id=user_id,
        reason_code=reason_code,
        window_minutes=window_minutes,
        limit=limit,
    )
    return UnbindAuditResponse(
        phone_e164=phone_e164,
        user_id=user_id,
        reason_code=reason_code,
        window_minutes=window_minutes,
        total=len(entries),
        entries=entries,
    )


@router.get("/v1/aliases/audit/unbind/users", response_model=UnbindUserSummaryListResponse)
def list_unbind_user_summaries(
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    users = _svc.list_unbind_user_summaries(
        db,
        window_minutes=window_minutes,
        limit=limit,
    )
    return UnbindUserSummaryListResponse(
        total_users=len(users),
        window_minutes=window_minutes,
        users=users,
    )


@router.get("/v1/aliases/audit/discoverability-reasons", response_model=DiscoverabilityReasonSummaryListResponse)
def list_discoverability_reason_summaries(
    reason_code: Optional[str] = None,
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    reasons = _svc.list_discoverability_reason_summaries(
        db,
        reason_code=reason_code,
        window_minutes=window_minutes,
        limit=limit,
    )
    return DiscoverabilityReasonSummaryListResponse(
        reason_code=reason_code,
        total_reasons=len(reasons),
        window_minutes=window_minutes,
        reasons=reasons,
    )


@router.get("/v1/aliases/audit/lifecycle/summary", response_model=LifecycleAuditSummaryResponse)
def get_lifecycle_audit_summary(
    phone_e164: Optional[str] = None,
    user_id: Optional[str] = None,
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return _svc.get_lifecycle_audit_summary(
        db,
        window_minutes=window_minutes,
        phone_e164=phone_e164,
        user_id=user_id,
        limit=limit,
    )


@router.get("/v1/aliases/audit/discoverability", response_model=DiscoverabilityAuditResponse)
def get_discoverability_audit(
    phone_e164: Optional[str] = None,
    user_id: Optional[str] = None,
    reason_code: Optional[str] = None,
    window_minutes: Optional[int] = Query(default=None, ge=1, le=1440),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    entries = _svc.query_discoverability_audit(
        db,
        phone_e164=phone_e164,
        user_id=user_id,
        reason_code=reason_code,
        window_minutes=window_minutes,
        limit=limit,
    )
    return DiscoverabilityAuditResponse(
        phone_e164=phone_e164,
        user_id=user_id,
        reason_code=reason_code,
        window_minutes=window_minutes,
        total=len(entries),
        entries=entries,
    )


@router.get("/v1/aliases/audit/discoverability/users", response_model=DiscoverabilityUserSummaryListResponse)
def list_discoverability_user_summaries(
    window_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    users = _svc.list_discoverability_user_summaries(
        db,
        window_minutes=window_minutes,
        limit=limit,
    )
    return DiscoverabilityUserSummaryListResponse(
        total_users=len(users),
        window_minutes=window_minutes,
        users=users,
    )


@router.get("/v1/aliases/recycled", response_model=RecycledAliasListResponse)
def list_recycled_aliases(
    user_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    aliases = _svc.list_recycled_aliases(db, user_id=user_id, limit=limit)
    return RecycledAliasListResponse(user_id=user_id, total=len(aliases), aliases=aliases)


@router.get("/v1/aliases/undiscoverable", response_model=UndiscoverableAliasListResponse)
def list_undiscoverable_aliases(
    user_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    aliases = _svc.list_undiscoverable_aliases(db, user_id=user_id, limit=limit)
    return UndiscoverableAliasListResponse(user_id=user_id, total=len(aliases), aliases=aliases)


@router.get("/v1/aliases/{alias_id}", response_model=AliasResponse)
def get_alias(alias_id: str, db: Session = Depends(get_db)):
    alias = _svc.get_alias_by_id(db, alias_id)
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    return alias


@router.get("/v1/aliases/history/{phone_e164:path}", response_model=AliasHistoryResponse)
def get_alias_history(
    phone_e164: str,
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    alias_status = None
    if status is not None:
        try:
            alias_status = AliasStatus(status)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid alias status filter")
    aliases = _svc.get_alias_history(db, phone_e164, status=alias_status)
    return AliasHistoryResponse(phone_e164=phone_e164, status=status, total=len(aliases), aliases=aliases)


@router.get("/v1/healthz", status_code=204)
def healthz():
    return Response(status_code=204)
