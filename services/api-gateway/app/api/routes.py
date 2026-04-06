from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response

from app.clients.connector_client import ConnectorClient
from app.clients.orchestrator_client import OrchestratorClient
from app.clients.reconciliation_client import ReconciliationClient

router = APIRouter(prefix="/v1", tags=["api-gateway"])
_client = OrchestratorClient()
_connector_client = ConnectorClient()
_reconciliation_client = ReconciliationClient()


def _forward_headers(request: Request) -> dict:
    return {
        "Idempotency-Key": request.headers.get("Idempotency-Key", ""),
        "X-Request-Id": getattr(request.state, "request_id", ""),
    }


@router.post("/transfers")
async def create_transfer(payload: dict, request: Request):
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
):
    params = {k: v for k, v in {"sender_user_id": sender_user_id, "status": status, "limit": limit, "cursor": cursor}.items() if v is not None}
    resp = await _client.list_transfers(params=params, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/transfers/{transfer_id}")
async def get_transfer(transfer_id: str, request: Request):
    resp = await _client.get_transfer(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/{transfer_id}/transition")
async def transition_transfer(transfer_id: str, payload: dict, request: Request):
    resp = await _client.transition_transfer(transfer_id=transfer_id, payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: str, request: Request):
    resp = await _client.cancel_transfer(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/transfers/{transfer_id}/events")
async def list_transfer_events(transfer_id: str, request: Request):
    resp = await _client.list_transfer_events(transfer_id=transfer_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/callbacks/connector")
async def connector_callback(payload: dict, request: Request):
    resp = await _client.connector_callback(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream orchestrator unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/transfers/events/relay")
async def relay_transfer_events(request: Request, limit: int = 100):
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
    resp = await _connector_client.get_transaction(external_ref=external_ref, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/connectors/transactions")
async def list_connector_transactions(request: Request):
    resp = await _connector_client.list_transactions(headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/connectors/simulate-callback")
async def simulate_connector_callback(payload: dict, request: Request):
    resp = await _connector_client.simulate_callback(payload=payload, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream connector unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.post("/reconciliation/runs")
async def run_reconciliation(request: Request):
    resp = await _reconciliation_client.run_reconciliation(headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream reconciliation unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/reconciliation/runs/{run_id}")
async def get_reconciliation_run(run_id: str, request: Request):
    resp = await _reconciliation_client.get_reconciliation_run(run_id=run_id, headers=_forward_headers(request))
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail="upstream reconciliation unavailable")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@router.get("/healthz", status_code=204)
async def healthz() -> Response:
    return Response(status_code=204)
