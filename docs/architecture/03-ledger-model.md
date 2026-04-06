# Ledger Model v0.1

Date: 2026-04-05

## 1. Principles
- Double-entry only, no single-sided balance mutation.
- Journal is append-only.
- Every posting set must net to zero.
- Idempotent posting by external reference.

## 2. Account Types (MVP)
- USER_AVAILABLE
- USER_PENDING
- TREASURY
- FEES_REVENUE
- CONNECTOR_SETTLEMENT
- DISPUTE_HOLD

## 3. Core Tables (Logical)
### ledger_account
- account_id (uuid)
- owner_type (USER | SYSTEM)
- owner_id (nullable)
- account_type
- currency
- status
- created_at

### journal_entry
- entry_id (uuid)
- external_ref (unique)
- transfer_id (nullable)
- entry_type (TRANSFER | REFUND | REVERSAL | ADJUSTMENT)
- created_at

### journal_posting
- posting_id (uuid)
- entry_id (fk)
- account_id (fk)
- direction (DEBIT | CREDIT)
- amount_minor (bigint)
- currency
- created_at

## 4. Invariants
- Sum(DEBIT) == Sum(CREDIT) for each entry_id.
- No cross-currency postings in a single entry.
- account currency must match posting currency.

## 5. Posting Templates
### P2P Transfer Reserve
1. DEBIT USER_AVAILABLE
2. CREDIT USER_PENDING

### Payout Submission
1. DEBIT USER_PENDING
2. CREDIT CONNECTOR_SETTLEMENT

### Settlement Confirmed
1. DEBIT CONNECTOR_SETTLEMENT
2. CREDIT TREASURY

### Refund
1. DEBIT TREASURY
2. CREDIT USER_AVAILABLE

## 6. Balance Strategy
- Balance snapshots stored per account for fast reads.
- Snapshots recalculated by applying new postings in order.
- Rebuild job can recompute balances from journal for recovery.

## 7. Auditability
- entry_id and external_ref tie back to transfer_id and request_id.
- All admin adjustments require reason code and actor_id.
