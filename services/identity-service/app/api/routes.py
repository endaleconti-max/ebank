from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.domain.errors import DuplicateUserError, InvalidAccountTransitionError, InvalidKycTransitionError, UserNotFoundError
from app.domain.models import KycStatus
from app.domain.schemas import (
    AccountAuditLogEntry,
    AccountStatusChangeRequest,
    CreateUserRequest,
    KycDecisionRequest,
    KycSubmissionRequest,
    UserResponse,
    UserStatusResponse,
)
from app.domain.service import IdentityService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/v1", tags=["identity"])

# This simple in-memory cache is a bootstrap idempotency mechanism for local dev.
IDEMPOTENCY_CACHE: dict[str, str] = {}


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    svc = IdentityService(db)

    if idempotency_key and idempotency_key in IDEMPOTENCY_CACHE:
        cached_user = svc.get_user(IDEMPOTENCY_CACHE[idempotency_key])
        return UserResponse.model_validate(cached_user)

    try:
        user = svc.create_user(payload.full_name, payload.country_code, str(payload.email))
    except DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if idempotency_key:
        IDEMPOTENCY_CACHE[idempotency_key] = user.user_id

    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    svc = IdentityService(db)
    try:
        user = svc.get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}/status", response_model=UserStatusResponse)
def get_user_status(user_id: str, db: Session = Depends(get_db)):
    svc = IdentityService(db)
    try:
        user = svc.get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return UserStatusResponse(user_id=user.user_id, account_status=user.account_status, kyc_status=user.kyc_status)


@router.post("/users/{user_id}/kyc/submit", response_model=UserResponse)
def submit_kyc(
    user_id: str,
    payload: KycSubmissionRequest,
    db: Session = Depends(get_db),
):
    del payload
    svc = IdentityService(db)
    try:
        user = svc.submit_kyc(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidKycTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/kyc/decision", response_model=UserResponse)
def decide_kyc(user_id: str, payload: KycDecisionRequest, db: Session = Depends(get_db)):
    svc = IdentityService(db)
    try:
        user = svc.decide_kyc(user_id, payload.decision)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidKycTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserResponse.model_validate(user)


@router.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
def healthz() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Account lifecycle admin endpoints ─────────────────────────────────────────

def _actor_id(x_caller_id: Optional[str]) -> str:
    return x_caller_id or "unknown"


@router.post("/users/{user_id}/suspend", response_model=UserResponse)
def suspend_user(
    user_id: str,
    payload: AccountStatusChangeRequest,
    db: Session = Depends(get_db),
    x_caller_id: Optional[str] = Header(default=None, alias="X-Caller-Id"),
):
    svc = IdentityService(db)
    try:
        user = svc.suspend_account(user_id, reason=payload.reason, actor_id=_actor_id(x_caller_id))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidAccountTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/reinstate", response_model=UserResponse)
def reinstate_user(
    user_id: str,
    payload: AccountStatusChangeRequest,
    db: Session = Depends(get_db),
    x_caller_id: Optional[str] = Header(default=None, alias="X-Caller-Id"),
):
    svc = IdentityService(db)
    try:
        user = svc.reinstate_account(user_id, reason=payload.reason, actor_id=_actor_id(x_caller_id))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidAccountTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/close", response_model=UserResponse)
def close_user(
    user_id: str,
    payload: AccountStatusChangeRequest,
    db: Session = Depends(get_db),
    x_caller_id: Optional[str] = Header(default=None, alias="X-Caller-Id"),
):
    svc = IdentityService(db)
    try:
        user = svc.close_account(user_id, reason=payload.reason, actor_id=_actor_id(x_caller_id))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidAccountTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}/account-audit-log", response_model=list[AccountAuditLogEntry])
def get_account_audit_log(user_id: str, db: Session = Depends(get_db)):
    svc = IdentityService(db)
    try:
        svc.get_user(user_id)  # 404 if user does not exist
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return svc.list_account_audit_log(user_id)