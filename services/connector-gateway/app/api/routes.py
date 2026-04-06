from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.domain.errors import (
    ConnectorNotSupportedError,
    ConnectorTransactionNotFoundError,
    DuplicateExternalRefError,
)
from app.domain.models import RailOperation
from app.domain.schemas import (
    ConnectorStatus,
    ConnectorTransactionEventResponse,
    ConnectorTransactionResponse,
    ConnectorWebhookRequest,
    ExecuteRailRequest,
    SimulateCallbackRequest,
    SimulateCallbackResponse,
)
from app.domain.service import ConnectorGatewayService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/v1", tags=["connector-gateway"])


@router.post("/connectors/{connector_id}/payouts", response_model=ConnectorTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_payout(connector_id: str, payload: ExecuteRailRequest, db: Session = Depends(get_db)):
    svc = ConnectorGatewayService(db)
    try:
        txn = svc.execute(
            connector_id=connector_id,
            operation=RailOperation.PAYOUT,
            transfer_id=payload.transfer_id,
            external_ref=payload.external_ref,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            destination=payload.destination,
        )
    except ConnectorNotSupportedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateExternalRefError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ConnectorTransactionResponse.model_validate(txn)


@router.post("/connectors/{connector_id}/fundings", response_model=ConnectorTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_funding(connector_id: str, payload: ExecuteRailRequest, db: Session = Depends(get_db)):
    svc = ConnectorGatewayService(db)
    try:
        txn = svc.execute(
            connector_id=connector_id,
            operation=RailOperation.FUNDING,
            transfer_id=payload.transfer_id,
            external_ref=payload.external_ref,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            destination=payload.destination,
        )
    except ConnectorNotSupportedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateExternalRefError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ConnectorTransactionResponse.model_validate(txn)


@router.post("/connectors/{connector_id}/webhooks", response_model=ConnectorTransactionResponse)
def webhook(connector_id: str, payload: ConnectorWebhookRequest, db: Session = Depends(get_db)):
    del connector_id
    svc = ConnectorGatewayService(db)
    try:
        txn = svc.apply_webhook(
            external_ref=payload.external_ref,
            status=payload.status,
            provider_response_code=payload.provider_response_code,
            provider_response_body=payload.provider_response_body,
        )
    except ConnectorTransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ConnectorTransactionResponse.model_validate(txn)


@router.post("/connectors/simulate-callback", response_model=SimulateCallbackResponse)
def simulate_callback(payload: SimulateCallbackRequest, db: Session = Depends(get_db)):
    svc = ConnectorGatewayService(db)
    try:
        txn = svc.simulate_callback(payload.external_ref, payload.status)
    except ConnectorTransactionNotFoundError:
        return SimulateCallbackResponse(accepted=False)

    return SimulateCallbackResponse(accepted=True, transaction=ConnectorTransactionResponse.model_validate(txn))


@router.get("/connectors/transactions/{external_ref}", response_model=ConnectorTransactionResponse)
def get_transaction(external_ref: str, db: Session = Depends(get_db)):
    svc = ConnectorGatewayService(db)
    try:
        txn = svc.get_transaction(external_ref)
    except ConnectorTransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ConnectorTransactionResponse.model_validate(txn)


@router.get("/connectors/transactions", response_model=list[ConnectorTransactionResponse])
def list_transactions(db: Session = Depends(get_db)):
    svc = ConnectorGatewayService(db)
    rows = svc.list_transactions()
    return [ConnectorTransactionResponse.model_validate(row) for row in rows]


@router.get("/connectors/transaction-events", response_model=list[ConnectorTransactionEventResponse])
def list_transaction_events(
    db: Session = Depends(get_db),
    external_ref: Optional[str] = None,
    status: Optional[ConnectorStatus] = None,
):
    svc = ConnectorGatewayService(db)
    rows = svc.list_transaction_events(external_ref=external_ref, status=status)
    return [ConnectorTransactionEventResponse.model_validate(row) for row in rows]


@router.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
def healthz() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
