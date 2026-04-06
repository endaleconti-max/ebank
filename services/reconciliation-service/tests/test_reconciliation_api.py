import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.infrastructure.db import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state(tmp_path: Path) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    ledger_db = tmp_path / "ledger.db"
    connector_db = tmp_path / "connector.db"
    _seed_ledger_db(ledger_db)
    _seed_connector_db(connector_db)

    settings.ledger_db_path = str(ledger_db)
    settings.connector_db_path = str(connector_db)


def _seed_ledger_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE journal_entries (
            entry_id TEXT PRIMARY KEY,
            external_ref TEXT NOT NULL,
            transfer_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE journal_postings (
            posting_id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            amount_minor INTEGER NOT NULL,
            currency TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        INSERT INTO journal_entries VALUES ('e1', 'ref-match', 't1', 'TRANSFER', '2026-04-05T00:00:00Z');
        INSERT INTO journal_entries VALUES ('e2', 'ref-no-connector', 't2', 'TRANSFER', '2026-04-05T00:00:00Z');
        INSERT INTO journal_entries VALUES ('e3', 'ref-amount-mismatch', 't3', 'TRANSFER', '2026-04-05T00:00:00Z');
        INSERT INTO journal_entries VALUES ('e4', 'ref-connector-failed', 't4', 'TRANSFER', '2026-04-05T00:00:00Z');

        INSERT INTO journal_postings VALUES ('p1', 'e1', 'a1', 'DEBIT', 1000, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p2', 'e1', 'a2', 'CREDIT', 1000, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p3', 'e2', 'a1', 'DEBIT', 700, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p4', 'e2', 'a2', 'CREDIT', 700, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p5', 'e3', 'a1', 'DEBIT', 500, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p6', 'e3', 'a2', 'CREDIT', 500, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p7', 'e4', 'a1', 'DEBIT', 900, 'USD', '2026-04-05T00:00:00Z');
        INSERT INTO journal_postings VALUES ('p8', 'e4', 'a2', 'CREDIT', 900, 'USD', '2026-04-05T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()


def _seed_connector_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE connector_transactions (
            connector_txn_id TEXT PRIMARY KEY,
            connector_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            transfer_id TEXT NOT NULL,
            external_ref TEXT NOT NULL,
            amount_minor INTEGER NOT NULL,
            currency TEXT NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL,
            provider_response_code TEXT,
            provider_response_body TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO connector_transactions VALUES ('c1', 'mock-bank-a', 'PAYOUT', 't1', 'ref-match', 1000, 'USD', 'acct-1', 'CONFIRMED', 'OK', '{}', '2026-04-05T00:00:00Z', '2026-04-05T00:00:00Z');
        INSERT INTO connector_transactions VALUES ('c2', 'mock-bank-a', 'PAYOUT', 't3', 'ref-amount-mismatch', 400, 'USD', 'acct-2', 'CONFIRMED', 'OK', '{}', '2026-04-05T00:00:00Z', '2026-04-05T00:00:00Z');
        INSERT INTO connector_transactions VALUES ('c3', 'mock-bank-a', 'PAYOUT', 't4', 'ref-connector-failed', 900, 'USD', 'acct-3', 'FAILED', 'ERR', '{}', '2026-04-05T00:00:00Z', '2026-04-05T00:00:00Z');
        INSERT INTO connector_transactions VALUES ('c4', 'mock-bank-b', 'PAYOUT', 't5', 'ref-orphan', 300, 'USD', 'acct-4', 'CONFIRMED', 'OK', '{}', '2026-04-05T00:00:00Z', '2026-04-05T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()


def test_reconciliation_run_finds_matches_and_mismatches() -> None:
    resp = client.post("/v1/reconciliation/runs")
    assert resp.status_code == 201

    body = resp.json()
    assert body["run"]["matched_count"] == 1
    assert body["run"]["mismatch_count"] == 4

    mismatch_types = {item["mismatch_type"] for item in body["mismatches"]}
    assert mismatch_types == {
        "MISSING_CONNECTOR_TRANSACTION",
        "AMOUNT_MISMATCH",
        "CONNECTOR_FAILED",
        "ORPHAN_CONNECTOR_TRANSACTION",
    }


def test_get_reconciliation_run_returns_persisted_result() -> None:
    create_resp = client.post("/v1/reconciliation/runs")
    run_id = create_resp.json()["run"]["run_id"]

    get_resp = client.get(f"/v1/reconciliation/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run"]["run_id"] == run_id
    assert len(get_resp.json()["mismatches"]) == 4
