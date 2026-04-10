from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional


@dataclass
class AuthorizationAuditEntry:
    caller_id: str
    method: str
    path: str
    required_permission: str
    allowed: bool
    reason: str
    request_id: str
    created_at: str


class AuthorizationAuditStore:
    def __init__(self, max_entries: int = 5000):
        self._entries: deque[AuthorizationAuditEntry] = deque(maxlen=max_entries)
        self._lock = Lock()

    def record(
        self,
        *,
        caller_id: str,
        method: str,
        path: str,
        required_permission: str,
        allowed: bool,
        reason: str,
        request_id: str,
        created_at: Optional[datetime] = None,
    ) -> None:
        timestamp = created_at or datetime.now(timezone.utc)
        entry = AuthorizationAuditEntry(
            caller_id=caller_id,
            method=method,
            path=path,
            required_permission=required_permission,
            allowed=allowed,
            reason=reason,
            request_id=request_id,
            created_at=timestamp.isoformat(),
        )
        with self._lock:
            self._entries.append(entry)

    def query(
        self,
        *,
        caller_id: Optional[str] = None,
        allowed: Optional[bool] = None,
        window_minutes: Optional[int] = None,
        limit: int = 100,
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        cutoff = None
        if window_minutes is not None:
            cutoff = now - timedelta(minutes=window_minutes)

        with self._lock:
            rows = list(self._entries)

        filtered: list[AuthorizationAuditEntry] = []
        for row in reversed(rows):
            if caller_id and row.caller_id != caller_id:
                continue
            if allowed is not None and row.allowed != allowed:
                continue
            if cutoff is not None:
                created = datetime.fromisoformat(row.created_at)
                if created < cutoff:
                    continue
            filtered.append(row)
            if len(filtered) >= limit:
                break

        return [asdict(item) for item in filtered]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_audit_store = AuthorizationAuditStore()


def get_authorization_audit_store() -> AuthorizationAuditStore:
    return _audit_store
