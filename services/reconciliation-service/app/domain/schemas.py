from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from app.domain.models import MismatchType, RunStatus


class ReconciliationMismatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mismatch_id: str
    run_id: str
    external_ref: str
    mismatch_type: MismatchType
    detail: str
    created_at: datetime


class ReconciliationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    status: RunStatus
    total_records: int
    matched_count: int
    mismatch_count: int
    started_at: datetime
    completed_at: datetime


class ReconciliationRunDetailResponse(BaseModel):
    run: ReconciliationRunResponse
    mismatches: List[ReconciliationMismatchResponse]
