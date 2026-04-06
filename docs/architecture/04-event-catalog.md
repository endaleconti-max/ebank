# Event Catalog v0.1

Date: 2026-04-05

## 1. Envelope
{
  "eventId": "uuid",
  "eventType": "TransferCreated",
  "eventVersion": "1.0.0",
  "occurredAt": "ISO-8601",
  "correlationId": "uuid",
  "payload": {}
}

## 2. Transfer Events
- TransferCreated
- TransferValidated
- TransferRiskApproved
- TransferComplianceApproved
- TransferReserved
- TransferSubmittedToRail
- TransferRailConfirmed
- TransferSettled
- TransferFailed
- TransferReversed

## 3. Alias Events
- AliasPhoneVerified
- AliasBound
- AliasUnbound
- AliasOwnershipChanged

## 4. Ledger Events
- JournalEntryCreated
- JournalEntryReversed
- LedgerInvariantViolationDetected

## 5. Compliance and Risk Events
- RiskDecisionProduced
- ComplianceDecisionProduced
- TransactionFlagRaised

## 6. Reconciliation Events
- ReconciliationMatchFound
- ReconciliationMismatchFound
- ReconciliationMismatchResolved

## 7. Notification Events
- UserNotificationRequested
- UserNotificationDelivered
- UserNotificationFailed

## 8. Topic Layout (Proposed)
- ebank.transfer.v1
- ebank.alias.v1
- ebank.ledger.v1
- ebank.risk.v1
- ebank.compliance.v1
- ebank.recon.v1
- ebank.notification.v1
