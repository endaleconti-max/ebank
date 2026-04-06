from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.domain.errors import (
    AliasAlreadyBoundError,
    AliasNotFoundError,
    PhoneNotVerifiedError,
    VerificationNotFoundError,
)
from app.domain.schemas import (
    AliasResponse,
    BindAliasRequest,
    ResolveAliasResponse,
    UnbindAliasRequest,
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


@router.get("/v1/aliases/resolve", response_model=ResolveAliasResponse)
def resolve_alias(phone_e164: str, db: Session = Depends(get_db)):
    alias = _svc.resolve_alias(db, phone_e164)
    if alias is None:
        return ResolveAliasResponse(found=False)
    return ResolveAliasResponse(found=True, alias=alias)


@router.get("/v1/healthz", status_code=204)
def healthz():
    return Response(status_code=204)
