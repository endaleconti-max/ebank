# Service Contracts v0.1

Date: 2026-04-05

## 1. API Gateway Contracts
### Required Headers
- Authorization: Bearer token
- Idempotency-Key: required on transfer creation and refund operations
- X-Request-Id: optional client value, generated if absent

## 2. Identity Service
### Commands
- POST /v1/users
- POST /v1/users/{userId}/kyc/submit
- POST /v1/users/{userId}/kyc/decision
### Queries
- GET /v1/users/{userId}
- GET /v1/users/{userId}/status

## 3. Alias Service
### Commands
- POST /v1/aliases/verify-phone
- POST /v1/aliases/bind
- POST /v1/aliases/unbind
### Queries
- GET /v1/aliases/resolve?phone={e164}
- GET /v1/aliases/{aliasId}

## 4. Payment Orchestrator
### Commands
- POST /v1/transfers
- POST /v1/transfers/{transferId}/cancel
- POST /v1/transfers/{transferId}/refund
### Queries
- GET /v1/transfers/{transferId}
- GET /v1/transfers?userId={userId}&limit={n}&cursor={token}

## 5. Ledger Service
### Commands
- POST /v1/ledger/postings
- POST /v1/ledger/reversals
### Queries
- GET /v1/ledger/accounts/{accountId}/balance
- GET /v1/ledger/entries/{entryId}

## 6. Connector Gateway
### Commands
- POST /v1/connectors/{connectorId}/payouts
- POST /v1/connectors/{connectorId}/fundings
### Async Inputs
- POST /v1/connectors/{connectorId}/webhooks

## 7. Common Response Envelope
{
  "requestId": "string",
  "data": {},
  "error": {
    "code": "string",
    "message": "string",
    "retryable": true
  }
}

## 8. Idempotency Rules
- Key uniqueness scope: method + path + principal + key.
- Replay window: 24h for transfer APIs.
- Duplicate request returns original status and body.

## 9. Transfer State Model
- CREATED
- VALIDATED
- RISK_REVIEW
- COMPLIANCE_REVIEW
- RESERVED
- SUBMITTED_TO_RAIL
- RAIL_CONFIRMED
- SETTLED
- FAILED
- REVERSED

Allowed transitions are enforced only by payment-orchestrator.
