from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request, Response

from app.clients.alias_client import AliasClient
from app.clients.connector_client import ConnectorClient
from app.clients.identity_client import IdentityClient
from app.clients.orchestrator_client import OrchestratorClient
from app.clients.reconciliation_client import ReconciliationClient
from app.config import settings
from app.domain.authorization_audit import get_authorization_audit_store
from app.domain.auth_models import Permission

router = APIRouter(prefix="/v1", tags=["api-gateway"])
_client = OrchestratorClient()
_connector_client = ConnectorClient()
_reconciliation_client = ReconciliationClient()
_identity_client = IdentityClient()
_alias_client = AliasClient()
_authz_audit_store = get_authorization_audit_store()

TransferEventStatusFilter = Literal[
    "CREATED",
    "VALIDATED",
    "RESERVED",
    "SUBMITTED_TO_RAIL",
    "SETTLED",
    "FAILED",
    "REVERSED",
]


def _forward_headers(request: Request) -> dict:
    headers = {
        "Idempotency-Key": request.headers.get("Idempotency-Key", ""),
        "X-Request-Id": getattr(request.state, "request_id", ""),
    }
    
    # Propagate authenticated caller identity to downstream services
    if hasattr(request.state, "identity") and request.state.identity:
        identity_headers = request.state.identity.to_headers()
        headers.update(identity_headers)
    
    return headers


def _authorize(request: Request, permission: Permission) -> None:
    if not settings.enforce_authorization:
        return
    identity = getattr(request.state, "identity", None)
    caller_id = getattr(identity, "caller_id", "unknown") if identity else "unknown"
    request_id = getattr(request.state, "request_id", "")
    if identity is None:
        _authz_audit_store.record(
            caller_id=caller_id,
            method=request.method,
            path=request.url.path,
            required_permission=permission.value,
            allowed=False,
            reason="missing_identity",
            request_id=request_id,
        )
        raise HTTPException(status_code=401, detail="missing authenticated identity")
    if not identity.has_permission(permission):
        _authz_audit_store.record(
            caller_id=caller_id,
            method=request.method,
            path=request.url.path,
            required_permission=permission.value,
            allowed=False,
            reason="missing_permission",
            request_id=request_id,
        )
        raise HTTPException(
            status_code=403,
            detail=f"missing required permission: {permission.value}",
        )
    _authz_audit_store.record(
        caller_id=caller_id,
        method=request.method,
        path=request.url.path,
        required_permission=permission.value,
        allowed=True,
        reason="authorized",
        request_id=request_id,
    )


@router.get("/auth/audit/authorization")
async def list_authorization_audit(
    request: Request,
    caller_id: Optional[str] = None,
    allowed: Optional[bool] = None,
    window_minutes: Optional[int] = None,
    limit: int = 100,
):
    _authorize(request, Permission.VIEW_AUTH_AUDIT)
    rows = _authz_audit_store.query(
        caller_id=caller_id,
        allowed=allowed,
        window_minutes=window_minutes,
        limit=limit,
    )
    return {
        "total": len(rows),
        "caller_id": caller_id,
        "allowed": allowed,
        "window_minutes": window_minutes,
        "limit": limit,
        "entries": rows,
    }


@router.post("/transfers")
async def create_transfer(payload: dict, request: Request):
    _authorize(request, Permission.CREATE_TRANSFER)
    resp = await _client.create_transfer(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/transfers")
async def list_transfers(
    request: Request,
    sender_user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
    created_at_from: Optional[str] = None,
    created_at_to: Optional[str] = None,
    q: Optional[str] = None,
):
    _authorize(request, Permission.LIST_TRANSFERS)
    params = {k: v for k, v in {
        "sender_user_id": sender_user_id,
        "status": status,
        "limit": limit,
        "cursor": cursor,
        "created_at_from": created_at_from,
        "created_at_to": created_at_to,
        "q": q,
    }.items() if v is not None}
    resp = await _client.list_transfers(params=params, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/transfers/{transfer_id}")
async def get_transfer(transfer_id: str, request: Request):
    _authorize(request, Permission.VIEW_TRANSFER)
    resp = await _client.get_transfer(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.patch("/transfers/{transfer_id}/note")
async def update_transfer_note(transfer_id: str, payload: dict, request: Request):
    _authorize(request, Permission.UPDATE_TRANSFER_NOTE)
    resp = await _client.update_transfer_note(
        transfer_id=transfer_id,
        payload=payload,
        headers=_forward_headers(request),
    )
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/{transfer_id}/transition")
async def transition_transfer(transfer_id: str, payload: dict, request: Request):
    _authorize(request, Permission.TRANSITION_TRANSFER)
    resp = await _client.transition_transfer(transfer_id=transfer_id, payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: str, request: Request):
    _authorize(request, Permission.CANCEL_TRANSFER)
    resp = await _client.cancel_transfer(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/transfers/{transfer_id}/events")
async def list_transfer_events(
    transfer_id: str,
    request: Request,
    event_type: Optional[str] = None,
    to_status: Optional[TransferEventStatusFilter] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    created_at_from: Optional[str] = None,
    created_at_to: Optional[str] = None,
):
    _authorize(request, Permission.VIEW_TRANSFER)
    params = {}
    if event_type:
        params["event_type"] = event_type
    if to_status:
        params["to_status"] = to_status
    if limit is not None:
        params["limit"] = limit
    if cursor:
        params["cursor"] = cursor
    if created_at_from:
        params["created_at_from"] = created_at_from
    if created_at_to:
        params["created_at_to"] = created_at_to
    resp = await _client.list_transfer_events(
        transfer_id=transfer_id,
        params=params,
        headers=_forward_headers(request),
    )
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    out = Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    next_cursor = None
    if hasattr(resp, "headers"):
        headers_obj = getattr(resp, "headers")
        next_cursor = headers_obj.get("X-Next-Cursor") or headers_obj.get("x-next-cursor")
    if next_cursor is not None:
        out.headers["X-Next-Cursor"] = next_cursor
    return out


@router.get("/transfers/{transfer_id}/events/summary")
async def transfer_event_summary(transfer_id: str, request: Request):
    _authorize(request, Permission.VIEW_TRANSFER)
    resp = await _client.get_transfer_event_summary(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/callbacks/connector")
async def connector_callback(payload: dict, request: Request):
    _authorize(request, Permission.TRANSITION_TRANSFER)
    resp = await _client.connector_callback(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/events/relay")
async def relay_transfer_events(request: Request, limit: int = 100):
    _authorize(request, Permission.VIEW_TRANSFER)
    resp = await _client.relay_events(limit=limit, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/connectors/transaction-events")
async def list_connector_transaction_events(
    request: Request,
    external_ref: Optional[str] = None,
    status: Optional[str] = None,
):
    _authorize(request, Permission.VIEW_CONNECTOR_TRANSACTIONS)
    params = {
        k: v
        for k, v in {
            "external_ref": external_ref,
            "status": status,
        }.items()
        if v is not None
    }
    resp = await _connector_client.list_transaction_events(params=params, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/connectors/transactions/{external_ref}")
async def get_connector_transaction(external_ref: str, request: Request):
    _authorize(request, Permission.VIEW_CONNECTOR_TRANSACTIONS)
    resp = await _connector_client.get_transaction(external_ref=external_ref, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/connectors/transactions")
async def list_connector_transactions(request: Request):
    _authorize(request, Permission.LIST_CONNECTORS)
    resp = await _connector_client.list_transactions(headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/connectors/simulate-callback")
async def simulate_connector_callback(payload: dict, request: Request):
    _authorize(request, Permission.SIMULATE_CONNECTOR_CALLBACK)
    resp = await _connector_client.simulate_callback(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/reconciliation/runs")
async def run_reconciliation(request: Request):
    _authorize(request, Permission.RUN_RECONCILIATION)
    resp = await _reconciliation_client.run_reconciliation(headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream reconciliation unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/reconciliation/runs/{run_id}")
async def get_reconciliation_run(run_id: str, request: Request):
    _authorize(request, Permission.VIEW_RECONCILIATION)
    resp = await _reconciliation_client.get_reconciliation_run(run_id=run_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream reconciliation unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


# ── Identity routes ──────────────────────────────────────────────────────────

@router.post("/users")
async def create_user(payload: dict, request: Request):
    _authorize(request, Permission.CREATE_USER)
    resp = await _identity_client.create_user(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream identity unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    _authorize(request, Permission.VIEW_USER)
    resp = await _identity_client.get_user(user_id=user_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream identity unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/users/{user_id}/status")
async def get_user_status(user_id: str, request: Request):
    _authorize(request, Permission.VIEW_USER)
    resp = await _identity_client.get_user_status(user_id=user_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream identity unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/users/{user_id}/kyc/submit")
async def submit_kyc(user_id: str, payload: dict, request: Request):
    _authorize(request, Permission.SUBMIT_KYC)
    resp = await _identity_client.submit_kyc(
        user_id=user_id, payload=payload, headers=_forward_headers(request)
    )
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream identity unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


# ── Alias routes ──────────────────────────────────────────────────────────────

@router.post("/aliases/verify-phone")
async def verify_phone(payload: dict, request: Request):
    _authorize(request, Permission.MANAGE_ALIASES)
    resp = await _alias_client.verify_phone(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream alias unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/aliases/bind")
async def bind_alias(payload: dict, request: Request):
    _authorize(request, Permission.MANAGE_ALIASES)
    resp = await _alias_client.bind_alias(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream alias unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/aliases/resolve")
async def resolve_alias(phone_e164: str, request: Request):
    _authorize(request, Permission.VIEW_ALIASES)
    resp = await _alias_client.resolve_alias(phone_e164=phone_e164, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream alias unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/healthz", status_code=204)
async def healthz() -> Response:
    return Response(status_code=204)
