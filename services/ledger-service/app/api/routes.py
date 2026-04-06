from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.domain.errors import (
    AccountNotFoundError,
    DuplicateExternalReferenceError,
    EntryNotFoundError,
    InactiveAccountError,
    InvariantViolationError,
)
from app.domain.schemas import (
    AccountResponse,
    BalanceResponse,
    CreateAccountRequest,
    CreatePostingRequest,
    EntrySummaryResponse,
    EntryResponse,
    PostingLineResponse,
    ReverseEntryRequest,
)
from app.domain.service import LedgerService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/v1", tags=["ledger"])


def _build_entry_response(entry, postings) -> EntryResponse:
    return EntryResponse(
        entry_id=entry.entry_id,
        external_ref=entry.external_ref,
        transfer_id=entry.transfer_id,
        entry_type=entry.entry_type,
        created_at=entry.created_at,
        postings=[
            PostingLineResponse(
                posting_id=posting.posting_id,
                account_id=posting.account_id,
                direction=posting.direction,
                amount_minor=posting.amount_minor,
                currency=posting.currency,
            )
            for posting in postings
        ],
    )


@router.post("/ledger/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(payload: CreateAccountRequest, db: Session = Depends(get_db)):
    svc = LedgerService(db)
    account = svc.create_account(payload.owner_type, payload.owner_id, payload.account_type, payload.currency)
    return AccountResponse.model_validate(account)


@router.post("/ledger/postings", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
def create_postings(payload: CreatePostingRequest, db: Session = Depends(get_db)):
    svc = LedgerService(db)
    try:
        entry, postings = svc.create_entry(
            external_ref=payload.external_ref,
            transfer_id=payload.transfer_id,
            entry_type=payload.entry_type,
            posting_lines=payload.postings,
        )
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvariantViolationError, InactiveAccountError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DuplicateExternalReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _build_entry_response(entry, postings)


@router.post("/ledger/reversals/{entry_id}", response_model=EntryResponse)
def reverse_entry(entry_id: str, payload: ReverseEntryRequest, db: Session = Depends(get_db)):
    svc = LedgerService(db)
    try:
        entry, postings = svc.reverse_entry(entry_id, payload.reversal_external_ref)
    except EntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateExternalReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (InvariantViolationError, InactiveAccountError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _build_entry_response(entry, postings)


@router.get("/ledger/accounts/{account_id}/balance", response_model=BalanceResponse)
def get_balance(account_id: str, db: Session = Depends(get_db)):
    svc = LedgerService(db)
    try:
        currency, balance_minor = svc.get_balance(account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BalanceResponse(account_id=account_id, currency=currency, balance_minor=balance_minor)


@router.get("/ledger/entries/{entry_id}", response_model=EntryResponse)
def get_entry(entry_id: str, db: Session = Depends(get_db)):
    svc = LedgerService(db)
    try:
        entry, postings = svc.get_entry(entry_id)
    except EntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _build_entry_response(entry, postings)


@router.get("/ledger/entries", response_model=list[EntrySummaryResponse])
def list_entries(db: Session = Depends(get_db)):
    svc = LedgerService(db)
    rows = svc.list_entry_summaries()
    return [EntrySummaryResponse(**row) for row in rows]


@router.get("/healthz", status_code=status.HTTP_204_NO_CONTENT)
def healthz() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
