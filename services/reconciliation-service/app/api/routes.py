from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.domain.errors import ReconciliationRunNotFoundError, SourceDatabaseError
from app.domain.schemas import (
    ReconciliationMismatchResponse,
    ReconciliationRunDetailResponse,
    ReconciliationRunResponse,
)
from app.domain.service import ReconciliationService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/v1", tags=["reconciliation"])


@router.post("/reconciliation/runs", response_model=ReconciliationRunDetailResponse, status_code=status.HTTP_201_CREATED)
def run_reconciliation(db: Session = Depends(get_db)):
    svc = ReconciliationService(db)
    try:
        run, mismatches = svc.run_reconciliation()
    except SourceDatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return ReconciliationRunDetailResponse(
        run=ReconciliationRunResponse.model_validate(run),
        mismatches=[ReconciliationMismatchResponse.model_validate(item) for item in mismatches],
    )


@router.get("/reconciliation/runs/{run_id}", response_model=ReconciliationRunDetailResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    svc = ReconciliationService(db)
    try:
        run, mismatches = svc.get_run(run_id)
    except ReconciliationRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ReconciliationRunDetailResponse(
        run=ReconciliationRunResponse.model_validate(run),
        mismatches=[ReconciliationMismatchResponse.model_validate(item) for item in mismatches],
    )


@router.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
def healthz() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
