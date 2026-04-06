from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import httpx
from typing import Optional

from app.config import settings
from app.domain.adapters import mock_provider_callback_status, mock_provider_submit
from app.domain.errors import (
    ConnectorNotSupportedError,
    ConnectorTransactionNotFoundError,
    DuplicateExternalRefError,
)
from app.domain.models import ConnectorStatus, ConnectorTransaction, ConnectorTransactionEvent, RailOperation


SUPPORTED_CONNECTORS = {"mock-bank-a", "mock-bank-b"}


class ConnectorGatewayService:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        connector_id: str,
        operation: RailOperation,
        transfer_id: str,
        external_ref: str,
        amount_minor: int,
        currency: str,
        destination: str,
    ) -> ConnectorTransaction:
        if connector_id not in SUPPORTED_CONNECTORS:
            raise ConnectorNotSupportedError("connector is not supported")

        response_code, response_body = mock_provider_submit(external_ref, amount_minor)
        status = ConnectorStatus.PENDING if response_code == "MOCK_ACCEPTED" else ConnectorStatus.FAILED

        txn = ConnectorTransaction(
            connector_id=connector_id,
            operation=operation,
            transfer_id=transfer_id,
            external_ref=external_ref,
            amount_minor=amount_minor,
            currency=currency.upper(),
            destination=destination,
            status=status,
            provider_response_code=response_code,
            provider_response_body=response_body,
        )
        self.db.add(txn)
        self.db.flush()
        self._record_event(txn, event_type="CONNECTOR_TRANSACTION_SUBMITTED")
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateExternalRefError("external_ref already exists") from exc

        self.db.refresh(txn)
        return txn

    def apply_webhook(
        self,
        external_ref: str,
        status: ConnectorStatus,
        provider_response_code: Optional[str],
        provider_response_body: Optional[str],
    ) -> ConnectorTransaction:
        txn = self.db.execute(
            select(ConnectorTransaction).where(ConnectorTransaction.external_ref == external_ref)
        ).scalar_one_or_none()
        if txn is None:
            raise ConnectorTransactionNotFoundError("connector transaction not found")

        txn.status = status
        txn.provider_response_code = provider_response_code
        txn.provider_response_body = provider_response_body
        self._record_event(txn, event_type="CONNECTOR_CALLBACK_APPLIED")
        self.db.commit()
        self.db.refresh(txn)

        if settings.callback_forward_enabled:
            self._forward_callback_to_orchestrator(txn)

        return txn

    def _forward_callback_to_orchestrator(self, txn: ConnectorTransaction) -> bool:
        payload = {
            "external_ref": txn.external_ref,
            "status": txn.status.value,
            "failure_reason": (
                txn.provider_response_body
                if txn.status == ConnectorStatus.FAILED and txn.provider_response_body
                else None
            ),
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(settings.callback_forward_url, json=payload)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def simulate_callback(self, external_ref: str, status: ConnectorStatus) -> ConnectorTransaction:
        normalized_status = mock_provider_callback_status(status)
        return self.apply_webhook(
            external_ref=external_ref,
            status=normalized_status,
            provider_response_code="MOCK_CALLBACK",
            provider_response_body=f"simulated callback status={normalized_status}",
        )

    def get_transaction(self, external_ref: str) -> ConnectorTransaction:
        txn = self.db.execute(
            select(ConnectorTransaction).where(ConnectorTransaction.external_ref == external_ref)
        ).scalar_one_or_none()
        if txn is None:
            raise ConnectorTransactionNotFoundError("connector transaction not found")
        return txn

    def list_transactions(self) -> list[ConnectorTransaction]:
        return self.db.execute(select(ConnectorTransaction)).scalars().all()

    def list_transaction_events(
        self,
        external_ref: Optional[str] = None,
        status: Optional[ConnectorStatus] = None,
    ) -> list[ConnectorTransactionEvent]:
        stmt = select(ConnectorTransactionEvent)
        if external_ref:
            stmt = stmt.where(ConnectorTransactionEvent.external_ref == external_ref)
        if status is not None:
            stmt = stmt.where(ConnectorTransactionEvent.status == status)
        stmt = stmt.order_by(ConnectorTransactionEvent.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def _record_event(self, txn: ConnectorTransaction, event_type: str) -> None:
        event = ConnectorTransactionEvent(
            connector_txn_id=txn.connector_txn_id,
            external_ref=txn.external_ref,
            transfer_id=txn.transfer_id,
            connector_id=txn.connector_id,
            amount_minor=txn.amount_minor,
            currency=txn.currency,
            status=txn.status,
            event_type=event_type,
        )
        self.db.add(event)
