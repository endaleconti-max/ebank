from typing import List, Optional

from pydantic import BaseModel, field_validator


# ── Watchlist ─────────────────────────────────────────────────────────────────

ALLOWED_REASON_CODES = {
    "OFAC-SDN",
    "UN-SANCTIONS",
    "EU-SANCTIONS",
    "PEP",          # Politically Exposed Person
    "ADVERSE-MEDIA",
    "INTERNAL-BLOCK",
    "UNSPECIFIED",
}


class AddWatchlistEntryRequest(BaseModel):
    name: str
    country_code: Optional[str] = None
    reason_code: str = "UNSPECIFIED"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("reason_code")
    @classmethod
    def reason_code_allowed(cls, v: str) -> str:
        if v not in ALLOWED_REASON_CODES:
            raise ValueError(f"reason_code must be one of {sorted(ALLOWED_REASON_CODES)}")
        return v


class WatchlistEntryResponse(BaseModel):
    entry_id: str
    name: str
    country_code: Optional[str]
    reason_code: str
    active: bool
    added_at: str


class WatchlistListResponse(BaseModel):
    total: int
    entries: List[WatchlistEntryResponse]


# ── Screening ─────────────────────────────────────────────────────────────────

ALLOWED_SUBJECT_TYPES = {"user", "transfer", "counterparty"}


class ScreenRequest(BaseModel):
    subject_id: str
    subject_type: str = "user"
    name: str

    @field_validator("subject_id")
    @classmethod
    def subject_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("subject_id must not be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("subject_type")
    @classmethod
    def subject_type_allowed(cls, v: str) -> str:
        if v not in ALLOWED_SUBJECT_TYPES:
            raise ValueError(f"subject_type must be one of {sorted(ALLOWED_SUBJECT_TYPES)}")
        return v


class ScreenResponse(BaseModel):
    log_id: str
    subject_id: str
    name: str
    decision: str  # clear | hit | potential_match
    matched_entry_id: Optional[str]
    matched_entry_name: Optional[str]
    reason_code: Optional[str]


# ── Screening log ─────────────────────────────────────────────────────────────

class ScreeningLogEntry(BaseModel):
    log_id: str
    subject_id: str
    subject_type: str
    name: str
    decision: str
    matched_entry_id: Optional[str]
    matched_entry_name: Optional[str]
    reason_code: Optional[str]
    caller_id: Optional[str]
    screened_at: str


class ScreeningLogResponse(BaseModel):
    total: int
    subject_id: Optional[str]
    decision: Optional[str]
    window_minutes: Optional[int]
    limit: int
    entries: List[ScreeningLogEntry]
