"""
Compliance screening business logic.

Name matching strategy:
  1. Exact match (case-insensitive) → HIT
  2. Levenshtein distance <= settings.name_match_threshold → POTENTIAL_MATCH
  3. No match → CLEAR
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.models import ScreeningDecision, ScreeningLog, WatchlistEntry


# ── Levenshtein distance (pure Python, no deps) ───────────────────────────────

def _levenshtein(a: str, b: str) -> int:
    a, b = a.lower(), b.lower()
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


# ── Match a name against the active watchlist ─────────────────────────────────

def _find_match(
    db: Session, name: str
) -> Tuple[ScreeningDecision, Optional[WatchlistEntry]]:
    """Return (decision, matched_entry_or_None)."""
    entries: List[WatchlistEntry] = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.active == True)  # noqa: E712
        .all()
    )
    name_lower = name.lower().strip()

    # Pass 1: exact match
    for entry in entries:
        if entry.name.lower().strip() == name_lower:
            return ScreeningDecision.HIT, entry

    # Pass 2: fuzzy match within threshold
    for entry in entries:
        dist = _levenshtein(name, entry.name)
        if dist <= settings.name_match_threshold:
            return ScreeningDecision.POTENTIAL_MATCH, entry

    return ScreeningDecision.CLEAR, None


# ── Public service functions ──────────────────────────────────────────────────

def screen(
    db: Session,
    *,
    subject_id: str,
    subject_type: str,
    name: str,
    caller_id: Optional[str] = None,
) -> ScreeningLog:
    decision, matched = _find_match(db, name)
    log = ScreeningLog(
        subject_id=subject_id,
        subject_type=subject_type,
        name=name,
        decision=decision.value,
        matched_entry_id=matched.entry_id if matched else None,
        matched_entry_name=matched.name if matched else None,
        reason_code=matched.reason_code if matched else None,
        caller_id=caller_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def add_entry(
    db: Session,
    *,
    name: str,
    country_code: Optional[str],
    reason_code: str,
) -> WatchlistEntry:
    entry = WatchlistEntry(
        name=name,
        country_code=country_code,
        reason_code=reason_code,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_entries(db: Session, *, active_only: bool = False) -> List[WatchlistEntry]:
    q = db.query(WatchlistEntry)
    if active_only:
        q = q.filter(WatchlistEntry.active == True)  # noqa: E712
    return q.order_by(WatchlistEntry.added_at.asc()).all()


def deactivate_entry(db: Session, entry_id: str) -> bool:
    """Soft-delete: mark as inactive rather than purging the audit trail."""
    entry = db.get(WatchlistEntry, entry_id)
    if entry is None:
        return False
    entry.active = False
    db.commit()
    return True


def query_screening_log(
    db: Session,
    *,
    subject_id: Optional[str] = None,
    decision: Optional[str] = None,
    window_minutes: Optional[int] = None,
    limit: int = 100,
) -> List[ScreeningLog]:
    q = db.query(ScreeningLog)
    if subject_id:
        q = q.filter(ScreeningLog.subject_id == subject_id)
    if decision:
        q = q.filter(ScreeningLog.decision == decision)
    if window_minutes is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        q = q.filter(ScreeningLog.screened_at >= cutoff)
    return q.order_by(ScreeningLog.screened_at.desc()).limit(limit).all()
