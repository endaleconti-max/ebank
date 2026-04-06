import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.domain.errors import ReconciliationRunNotFoundError, SourceDatabaseError
from app.domain.models import MismatchType, ReconciliationMismatch, ReconciliationRun, RunStatus


class ReconciliationService:
    def __init__(self, db: Session):
        self.db = db

    def _read_ledger_records(self) -> Dict[str, dict]:
        if settings.source_mode.lower() == "service":
            return self._read_ledger_records_from_service()

        try:
            conn = sqlite3.connect(settings.ledger_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    je.external_ref AS external_ref,
                    SUM(CASE WHEN jp.direction = 'DEBIT' THEN jp.amount_minor ELSE 0 END) AS debit_total,
                    MIN(jp.currency) AS currency
                FROM journal_entries je
                JOIN journal_postings jp ON jp.entry_id = je.entry_id
                GROUP BY je.entry_id, je.external_ref
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as exc:
            raise SourceDatabaseError(f"ledger db read failed: {exc}") from exc

        records: Dict[str, dict] = {}
        for row in rows:
            records[row["external_ref"]] = {
                "amount_minor": int(row["debit_total"]),
                "currency": row["currency"],
            }
        return records

    def _read_connector_records(self) -> Dict[str, dict]:
        if settings.source_mode.lower() == "service":
            return self._read_connector_records_from_service()

        try:
            conn = sqlite3.connect(settings.connector_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT external_ref, amount_minor, currency, status, connector_id
                FROM connector_transactions
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as exc:
            raise SourceDatabaseError(f"connector db read failed: {exc}") from exc

        records: Dict[str, dict] = {}
        for row in rows:
            records[row["external_ref"]] = {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
                "status": row["status"],
                "connector_id": row["connector_id"],
            }
        return records

    def _read_ledger_records_from_service(self) -> Dict[str, dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{settings.ledger_service_base_url.rstrip('/')}/v1/ledger/entries"
                )
            response.raise_for_status()
            rows = response.json()
        except Exception as exc:
            raise SourceDatabaseError(f"ledger service read failed: {exc}") from exc

        records: Dict[str, dict] = {}
        for row in rows:
            records[row["external_ref"]] = {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
            }
        return records

    def _read_connector_records_from_service(self) -> Dict[str, dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{settings.connector_service_base_url.rstrip('/')}/v1/connectors/transactions"
                )
            response.raise_for_status()
            rows = response.json()
        except Exception as exc:
            raise SourceDatabaseError(f"connector service read failed: {exc}") from exc

        records: Dict[str, dict] = {}
        for row in rows:
            records[row["external_ref"]] = {
                "amount_minor": int(row["amount_minor"]),
                "currency": row["currency"],
                "status": row["status"],
                "connector_id": row["connector_id"],
            }
        return records

    def run_reconciliation(self) -> Tuple[ReconciliationRun, List[ReconciliationMismatch]]:
        started_at = datetime.now(timezone.utc)
        ledger_records = self._read_ledger_records()
        connector_records = self._read_connector_records()

        mismatches: List[ReconciliationMismatch] = []
        matched_count = 0

        for external_ref, ledger_record in ledger_records.items():
            connector_record = connector_records.get(external_ref)
            if connector_record is None:
                mismatches.append(
                    ReconciliationMismatch(
                        run_id="",
                        external_ref=external_ref,
                        mismatch_type=MismatchType.MISSING_CONNECTOR_TRANSACTION,
                        detail="ledger entry exists but connector transaction is missing",
                    )
                )
                continue

            if ledger_record["amount_minor"] != connector_record["amount_minor"]:
                mismatches.append(
                    ReconciliationMismatch(
                        run_id="",
                        external_ref=external_ref,
                        mismatch_type=MismatchType.AMOUNT_MISMATCH,
                        detail=(
                            f"ledger amount={ledger_record['amount_minor']} connector amount={connector_record['amount_minor']}"
                        ),
                    )
                )
                continue

            if ledger_record["currency"] != connector_record["currency"]:
                mismatches.append(
                    ReconciliationMismatch(
                        run_id="",
                        external_ref=external_ref,
                        mismatch_type=MismatchType.CURRENCY_MISMATCH,
                        detail=(
                            f"ledger currency={ledger_record['currency']} connector currency={connector_record['currency']}"
                        ),
                    )
                )
                continue

            if connector_record["status"] == "FAILED":
                mismatches.append(
                    ReconciliationMismatch(
                        run_id="",
                        external_ref=external_ref,
                        mismatch_type=MismatchType.CONNECTOR_FAILED,
                        detail="connector transaction is in FAILED status",
                    )
                )
                continue

            matched_count += 1

        for external_ref, connector_record in connector_records.items():
            if external_ref not in ledger_records:
                mismatches.append(
                    ReconciliationMismatch(
                        run_id="",
                        external_ref=external_ref,
                        mismatch_type=MismatchType.ORPHAN_CONNECTOR_TRANSACTION,
                        detail=(
                            f"connector transaction exists without ledger entry for connector={connector_record['connector_id']}"
                        ),
                    )
                )

        run = ReconciliationRun(
            status=RunStatus.COMPLETED,
            total_records=len(ledger_records) + sum(1 for ref in connector_records if ref not in ledger_records),
            matched_count=matched_count,
            mismatch_count=len(mismatches),
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()

        for mismatch in mismatches:
            mismatch.run_id = run.run_id
            self.db.add(mismatch)

        self.db.commit()
        self.db.refresh(run)
        for mismatch in mismatches:
            self.db.refresh(mismatch)

        return run, mismatches

    def get_run(self, run_id: str) -> Tuple[ReconciliationRun, List[ReconciliationMismatch]]:
        run = self.db.get(ReconciliationRun, run_id)
        if run is None:
            raise ReconciliationRunNotFoundError("reconciliation run not found")

        mismatches = self.db.execute(
            select(ReconciliationMismatch).where(ReconciliationMismatch.run_id == run_id)
        ).scalars().all()
        return run, mismatches
