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
    AliasResponse,
    BindAliasRequest,
    ResolveAliasResponse,
    ResolveAuditResponse,
    ResolveAuditSummaryResponse,
    UnbindAliasRequest,
    UpdateDiscoverableRequest,
    VerifyPhoneRequest,
    VerifyPhoneResponse,
)
from app.domain.service import AliasService
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


@router.get("/v1/aliases/audit/resolve", response_model=ResolveAuditResponse)
def get_resolve_audit(
    phone_e164: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    entries = _svc.get_resolve_audit(db, phone_e164, limit=limit)
    return ResolveAuditResponse(phone_e164=phone_e164, total=len(entries), entries=entries)


@router.get("/v1/aliases/audit/resolve/summary", response_model=ResolveAuditSummaryResponse)
def get_resolve_audit_summary(
    caller_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return _svc.get_resolve_audit_summary(db, caller_id=caller_id)


@router.get("/v1/aliases/{alias_id}", response_model=AliasResponse)
def get_alias(alias_id: str, db: Session = Depends(get_db)):
    alias = _svc.get_alias_by_id(db, alias_id)
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias not found")
    return alias


@router.get("/v1/aliases/history/{phone_e164:path}", response_model=AliasHistoryResponse)
def get_alias_history(phone_e164: str, db: Session = Depends(get_db)):
    aliases = _svc.get_alias_history(db, phone_e164)
    return AliasHistoryResponse(phone_e164=phone_e164, total=len(aliases), aliases=aliases)


@router.get("/v1/healthz", status_code=204)
def healthz():
    return Response(status_code=204)
