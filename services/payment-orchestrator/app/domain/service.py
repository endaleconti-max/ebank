import base64
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import (
    ConnectorCallbackTargetNotFoundError,
    DuplicateIdempotencyKeyError,
    InvalidTransferRequestError,
    InvalidTransitionError,
    TransferNotFoundError,
)
from app.config import settings
from app.domain.connector_client import submit_payout
from app.domain.ledger_client import post_transfer_entry
from app.domain.models import Transfer, TransferEvent, TransferStatus
from app.domain.prechecks import run_prechecks


ALLOWED_TRANSITIONS: dict[TransferStatus, set[TransferStatus]] = {
    TransferStatus.CREATED: {TransferStatus.VALIDATED, TransferStatus.FAILED},
    TransferStatus.VALIDATED: {TransferStatus.RESERVED, TransferStatus.FAILED},
    TransferStatus.RESERVED: {TransferStatus.SUBMITTED_TO_RAIL, TransferStatus.FAILED},
    TransferStatus.SUBMITTED_TO_RAIL: {TransferStatus.SETTLED, TransferStatus.FAILED, TransferStatus.REVERSED},
    TransferStatus.SETTLED: {TransferStatus.REVERSED},
    TransferStatus.FAILED: set(),
    TransferStatus.REVERSED: set(),
}


class PaymentOrchestratorService:
    def __init__(self, db: Session):
        self.db = db

    def create_transfer(
        self,
        idempotency_key: str,
        sender_user_id: str,
        recipient_phone_e164: str,
        currency: str,
        amount_minor: int,
        note: Optional[str],
        sender_ledger_account_id: Optional[str] = None,
        transit_ledger_account_id: Optional[str] = None,
    ) -> Transfer:
        if amount_minor <= 0:
            raise InvalidTransferRequestError("amount_minor must be > 0")

        existing = self.db.execute(
            select(Transfer).where(Transfer.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        transfer = Transfer(
            idempotency_key=idempotency_key,
            sender_user_id=sender_user_id,
            recipient_phone_e164=recipient_phone_e164,
            currency=currency.upper(),
            amount_minor=amount_minor,
            note=note,
            status=TransferStatus.CREATED,
            sender_ledger_account_id=sender_ledger_account_id,
            transit_ledger_account_id=transit_ledger_account_id,
        )
        self.db.add(transfer)
        self.db.flush()

        self._record_event(
            transfer=transfer,
            event_type="TRANSFER_CREATED",
            from_status=None,
            to_status=TransferStatus.CREATED,
            failure_reason=None,
        )

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateIdempotencyKeyError("idempotency key already exists") from exc

        self.db.refresh(transfer)
        return transfer

    def get_transfer(self, transfer_id: str) -> Transfer:
        transfer = self.db.get(Transfer, transfer_id)
        if transfer is None:
            raise TransferNotFoundError("transfer not found")
        return transfer

    def transition_transfer(
        self,
        transfer_id: str,
        next_status: TransferStatus,
        failure_reason: Optional[str] = None,
    ) -> Transfer:
        transfer = self.get_transfer(transfer_id)
        previous_status = transfer.status

        if next_status not in ALLOWED_TRANSITIONS[transfer.status]:
            raise InvalidTransitionError(f"invalid transition: {transfer.status} -> {next_status}")

        if transfer.status == TransferStatus.CREATED and next_status == TransferStatus.VALIDATED:
            precheck_ok, precheck_reason = run_prechecks(
                sender_user_id=transfer.sender_user_id,
                recipient_phone_e164=transfer.recipient_phone_e164,
                amount_minor=transfer.amount_minor,
                note=transfer.note,
            )
            if not precheck_ok:
                transfer.status = TransferStatus.FAILED
                transfer.failure_reason = precheck_reason
                self._record_event(
                    transfer=transfer,
                    event_type="TRANSFER_PRECHECK_FAILED",
                    from_status=previous_status,
                    to_status=TransferStatus.FAILED,
                    failure_reason=precheck_reason,
                )
                self.db.commit()
                self.db.refresh(transfer)
                return transfer

        if next_status in {TransferStatus.FAILED, TransferStatus.REVERSED} and not failure_reason:
            raise InvalidTransitionError("failure_reason is required for FAILED or REVERSED state")

        if transfer.status == TransferStatus.RESERVED and next_status == TransferStatus.SUBMITTED_TO_RAIL:
            if settings.connector_submission_enabled:
                submit_result = submit_payout(transfer)
                transfer.connector_external_ref = submit_result.get("external_ref")
                if submit_result.get("ok") != "true":
                    transfer.status = TransferStatus.FAILED
                    transfer.failure_reason = submit_result.get("reason", "connector_submission_failed")
                    self._record_event(
                        transfer=transfer,
                        event_type="TRANSFER_CONNECTOR_SUBMISSION_FAILED",
                        from_status=previous_status,
                        to_status=TransferStatus.FAILED,
                        failure_reason=transfer.failure_reason,
                    )
                    self.db.commit()
                    self.db.refresh(transfer)
                    return transfer

            if settings.ledger_posting_enabled:
                post_transfer_entry(transfer)

        transfer.status = next_status
        transfer.failure_reason = (
            failure_reason
            if next_status in {TransferStatus.FAILED, TransferStatus.REVERSED}
            else None
        )
        self._record_event(
            transfer=transfer,
            event_type="TRANSFER_STATUS_TRANSITIONED",
            from_status=previous_status,
            to_status=next_status,
            failure_reason=transfer.failure_reason,
        )
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def apply_connector_callback(
        self,
        external_ref: str,
        status: str,
        failure_reason: Optional[str] = None,
    ) -> Transfer:
        transfer = self.db.execute(
            select(Transfer).where(Transfer.connector_external_ref == external_ref)
        ).scalar_one_or_none()
        if transfer is None:
            raise ConnectorCallbackTargetNotFoundError("transfer not found for connector external_ref")

        normalized = status.upper()
        previous_status = transfer.status
        if normalized == "CONFIRMED":
            if transfer.status != TransferStatus.SUBMITTED_TO_RAIL:
                raise InvalidTransitionError(
                    f"invalid callback transition: {transfer.status} -> {TransferStatus.SETTLED}"
                )
            transfer.status = TransferStatus.SETTLED
            transfer.failure_reason = None
            self._record_event(
                transfer=transfer,
                event_type="TRANSFER_CONNECTOR_CALLBACK_CONFIRMED",
                from_status=previous_status,
                to_status=TransferStatus.SETTLED,
                failure_reason=None,
            )
        elif normalized == "FAILED":
            if transfer.status not in {TransferStatus.SUBMITTED_TO_RAIL, TransferStatus.RESERVED}:
                raise InvalidTransitionError(
                    f"invalid callback transition: {transfer.status} -> {TransferStatus.FAILED}"
                )
            transfer.status = TransferStatus.FAILED
            transfer.failure_reason = failure_reason or "connector_callback_failed"
            self._record_event(
                transfer=transfer,
                event_type="TRANSFER_CONNECTOR_CALLBACK_FAILED",
                from_status=previous_status,
                to_status=TransferStatus.FAILED,
                failure_reason=transfer.failure_reason,
            )
        else:
            raise InvalidTransitionError("unsupported connector callback status")

        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def list_transfer_events(self, transfer_id: str) -> list[TransferEvent]:
        transfer = self.get_transfer(transfer_id)
        del transfer
        return self.db.execute(
            select(TransferEvent)
            .where(TransferEvent.transfer_id == transfer_id)
            .order_by(TransferEvent.created_at.asc())
        ).scalars().all()

    def relay_unprocessed_events(self, limit: int = 100) -> list[TransferEvent]:
        events = self.db.execute(
            select(TransferEvent)
            .where(TransferEvent.relayed_at.is_(None))
            .order_by(TransferEvent.created_at.asc())
            .limit(limit)
        ).scalars().all()
        if not events:
            return []

        relay_time = datetime.now(timezone.utc)
        for event in events:
            event.relayed_at = relay_time
        self.db.commit()
        for event in events:
            self.db.refresh(event)
        return events

    def cancel_transfer(self, transfer_id: str) -> Transfer:
        transfer = self.get_transfer(transfer_id)
        cancellable = {TransferStatus.CREATED, TransferStatus.VALIDATED, TransferStatus.RESERVED}
        if transfer.status not in cancellable:
            raise InvalidTransitionError(
                f"cannot cancel transfer in status {transfer.status}"
            )
        previous_status = transfer.status
        transfer.status = TransferStatus.FAILED
        transfer.failure_reason = "CANCELLED"
        self._record_event(
            transfer=transfer,
            event_type="TRANSFER_CANCELLED",
            from_status=previous_status,
            to_status=TransferStatus.FAILED,
            failure_reason="CANCELLED",
        )
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def list_transfers(
        self,
        sender_user_id: Optional[str] = None,
        status: Optional[TransferStatus] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> tuple:
        offset = 0
        if cursor is not None:
            try:
                offset = int(base64.b64decode(cursor.encode()).decode())
            except Exception:
                pass

        conditions = []
        if sender_user_id is not None:
            conditions.append(Transfer.sender_user_id == sender_user_id)
        if status is not None:
            conditions.append(Transfer.status == status)

        q = select(Transfer)
        if conditions:
            q = q.where(and_(*conditions))
        q = q.order_by(Transfer.created_at.asc(), Transfer.transfer_id.asc()).offset(offset).limit(limit + 1)

        rows = list(self.db.execute(q).scalars().all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor: Optional[str] = None
        if has_more:
            next_cursor = base64.b64encode(str(offset + limit).encode()).decode()
        return rows, next_cursor

    def _record_event(
        self,
        transfer: Transfer,
        event_type: str,
        from_status: Optional[TransferStatus],
        to_status: Optional[TransferStatus],
        failure_reason: Optional[str],
    ) -> None:
        event = TransferEvent(
            transfer_id=transfer.transfer_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            failure_reason=failure_reason,
        )
        self.db.add(event)
