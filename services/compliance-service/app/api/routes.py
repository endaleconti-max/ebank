from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.domain import service as svc
from app.domain.models import get_db
from app.domain.schemas import (
    AddWatchlistEntryRequest,
    ScreenRequest,
    ScreenResponse,
    ScreeningLogEntry,
    ScreeningLogResponse,
    WatchlistEntryResponse,
    WatchlistListResponse,
)

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


@router.post("/screen", response_model=ScreenResponse, status_code=200)
def screen(payload: ScreenRequest, request: Request, db: Session = Depends(get_db)):
    caller_id = request.headers.get("X-Caller-Id")
    log = svc.screen(
        db,
        subject_id=payload.subject_id,
        subject_type=payload.subject_type,
        name=payload.name,
        caller_id=caller_id,
    )
    return ScreenResponse(
        log_id=log.log_id,
        subject_id=log.subject_id,
        name=log.name,
        decision=log.decision,
        matched_entry_id=log.matched_entry_id,
        matched_entry_name=log.matched_entry_name,
        reason_code=log.reason_code,
    )


@router.get("/watchlist", response_model=WatchlistListResponse)
def list_watchlist(active_only: bool = False, db: Session = Depends(get_db)):
    entries = svc.list_entries(db, active_only=active_only)
    return WatchlistListResponse(
        total=len(entries),
        entries=[
            WatchlistEntryResponse(
                entry_id=e.entry_id,
                name=e.name,
                country_code=e.country_code,
                reason_code=e.reason_code,
                active=e.active,
                added_at=e.added_at.isoformat(),
            )
            for e in entries
        ],
    )


@router.post("/watchlist", response_model=WatchlistEntryResponse, status_code=201)
def add_watchlist_entry(payload: AddWatchlistEntryRequest, db: Session = Depends(get_db)):
    entry = svc.add_entry(
        db,
        name=payload.name,
        country_code=payload.country_code,
        reason_code=payload.reason_code,
    )
    return WatchlistEntryResponse(
        entry_id=entry.entry_id,
        name=entry.name,
        country_code=entry.country_code,
        reason_code=entry.reason_code,
        active=entry.active,
        added_at=entry.added_at.isoformat(),
    )


@router.delete("/watchlist/{entry_id}", status_code=204)
def deactivate_watchlist_entry(entry_id: str, db: Session = Depends(get_db)):
    deleted = svc.deactivate_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="watchlist entry not found")


@router.get("/log", response_model=ScreeningLogResponse)
def query_log(
    subject_id: Optional[str] = None,
    decision: Optional[str] = None,
    window_minutes: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    entries = svc.query_screening_log(
        db,
        subject_id=subject_id,
        decision=decision,
        window_minutes=window_minutes,
        limit=limit,
    )
    return ScreeningLogResponse(
        total=len(entries),
        subject_id=subject_id,
        decision=decision,
        window_minutes=window_minutes,
        limit=limit,
        entries=[
            ScreeningLogEntry(
                log_id=e.log_id,
                subject_id=e.subject_id,
                subject_type=e.subject_type,
                name=e.name,
                decision=e.decision,
                matched_entry_id=e.matched_entry_id,
                matched_entry_name=e.matched_entry_name,
                reason_code=e.reason_code,
                caller_id=e.caller_id,
                screened_at=e.screened_at.isoformat(),
            )
            for e in entries
        ],
    )
