from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.domain.errors import (
    ConnectorCallbackTargetNotFoundError,
    InvalidTransitionError,
    TransferNotFoundError,
)
from app.domain.models import TransferStatus
from app.domain.schemas import (
    ConnectorCallbackRequest,
    CreateTransferRequest,
    TransferEventResponse,
    TransferEventRelayResponse,
    TransferListResponse,
    TransferResponse,
    TransitionTransferRequest,
)
from app.domain.service import PaymentOrchestratorService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/v1", tags=["orchestrator"])


@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: CreateTransferRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required")

    svc = PaymentOrchestratorService(db)
    transfer = svc.create_transfer(
        idempotency_key=idempotency_key,
        sender_user_id=payload.sender_user_id,
        recipient_phone_e164=payload.recipient_phone_e164,
        currency=payload.currency,
        amount_minor=payload.amount_minor,
        note=payload.note,
        sender_ledger_account_id=payload.sender_ledger_account_id,
        transit_ledger_account_id=payload.transit_ledger_account_id,
    )
    return TransferResponse.model_validate(transfer)


@router.get("/transfers", response_model=TransferListResponse)
def list_transfers(
    sender_user_id: Optional[str] = None,
    transfer_status: Optional[TransferStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = None,
    db: Session = Depends(get_db),
):
    svc = PaymentOrchestratorService(db)
    transfers, next_cursor = svc.list_transfers(
        sender_user_id=sender_user_id,
        status=transfer_status,
        limit=limit,
        cursor=cursor,
    )
    return TransferListResponse(
        transfers=[TransferResponse.model_validate(t) for t in transfers],
        next_cursor=next_cursor,
        count=len(transfers),
    )


@router.get("/transfers/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: str, db: Session = Depends(get_db)):
    svc = PaymentOrchestratorService(db)
    try:
        transfer = svc.get_transfer(transfer_id)
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TransferResponse.model_validate(transfer)


@router.post("/transfers/{transfer_id}/transition", response_model=TransferResponse)
def transition_transfer(transfer_id: str, payload: TransitionTransferRequest, db: Session = Depends(get_db)):
    svc = PaymentOrchestratorService(db)
    try:
        transfer = svc.transition_transfer(transfer_id, payload.status, payload.failure_reason)
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return TransferResponse.model_validate(transfer)


@router.post("/transfers/{transfer_id}/cancel", response_model=TransferResponse)
def cancel_transfer(transfer_id: str, db: Session = Depends(get_db)):
    svc = PaymentOrchestratorService(db)
    try:
        transfer = svc.cancel_transfer(transfer_id)
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TransferResponse.model_validate(transfer)


@router.post("/transfers/callbacks/connector", response_model=TransferResponse)
def connector_callback(payload: ConnectorCallbackRequest, db: Session = Depends(get_db)):
    svc = PaymentOrchestratorService(db)
    try:
        transfer = svc.apply_connector_callback(
            external_ref=payload.external_ref,
            status=payload.status,
            failure_reason=payload.failure_reason,
        )
    except ConnectorCallbackTargetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return TransferResponse.model_validate(transfer)


@router.get("/transfers/{transfer_id}/events", response_model=list[TransferEventResponse])
def list_transfer_events(transfer_id: str, db: Session = Depends(get_db)):
    svc = PaymentOrchestratorService(db)
    try:
        events = svc.list_transfer_events(transfer_id)
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [TransferEventResponse.model_validate(event) for event in events]


@router.post("/transfers/events/relay", response_model=TransferEventRelayResponse)
def relay_transfer_events(db: Session = Depends(get_db), limit: int = 100):
    svc = PaymentOrchestratorService(db)
    events = svc.relay_unprocessed_events(limit=limit)
    response_events = [TransferEventResponse.model_validate(event) for event in events]
    return TransferEventRelayResponse(events=response_events, exported_count=len(response_events))


@router.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
def healthz() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
