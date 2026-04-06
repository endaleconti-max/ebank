from collections import defaultdict
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import (
    AccountNotFoundError,
    DuplicateExternalReferenceError,
    EntryNotFoundError,
    InactiveAccountError,
    InvariantViolationError,
)
from app.domain.models import (
    AccountStatus,
    EntryType,
    JournalEntry,
    JournalPosting,
    LedgerAccount,
    PostingDirection,
)
from app.domain.schemas import PostingLineRequest


class LedgerService:
    def __init__(self, db: Session):
        self.db = db

    def create_account(self, owner_type: str, owner_id: str, account_type, currency: str) -> LedgerAccount:
        account = LedgerAccount(
            owner_type=owner_type,
            owner_id=owner_id,
            account_type=account_type,
            currency=currency.upper(),
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def create_entry(
        self,
        external_ref: str,
        transfer_id: str,
        entry_type: EntryType,
        posting_lines: List[PostingLineRequest],
    ) -> tuple[JournalEntry, List[JournalPosting]]:
        if len(posting_lines) < 2:
            raise InvariantViolationError("at least two postings are required")

        debit_total = 0
        credit_total = 0
        currencies = set()
        account_ids = set(line.account_id for line in posting_lines)

        accounts = self.db.execute(select(LedgerAccount).where(LedgerAccount.account_id.in_(account_ids))).scalars().all()
        account_map: Dict[str, LedgerAccount] = {account.account_id: account for account in accounts}

        if len(account_map) != len(account_ids):
            raise AccountNotFoundError("one or more accounts not found")

        for line in posting_lines:
            account = account_map[line.account_id]
            if account.status != AccountStatus.ACTIVE:
                raise InactiveAccountError("account is not active")
            if account.currency != line.currency.upper():
                raise InvariantViolationError("posting currency must match account currency")

            amount = line.amount_minor
            currencies.add(line.currency.upper())
            if line.direction == PostingDirection.DEBIT:
                debit_total += amount
            else:
                credit_total += amount

        if len(currencies) != 1:
            raise InvariantViolationError("all postings in one entry must have the same currency")
        if debit_total != credit_total:
            raise InvariantViolationError("entry is unbalanced")

        entry = JournalEntry(external_ref=external_ref, transfer_id=transfer_id, entry_type=entry_type)
        self.db.add(entry)
        self.db.flush()

        postings: List[JournalPosting] = []
        for line in posting_lines:
            posting = JournalPosting(
                entry_id=entry.entry_id,
                account_id=line.account_id,
                direction=line.direction,
                amount_minor=line.amount_minor,
                currency=line.currency.upper(),
            )
            postings.append(posting)
            self.db.add(posting)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateExternalReferenceError("external_ref already exists") from exc

        self.db.refresh(entry)
        for posting in postings:
            self.db.refresh(posting)

        return entry, postings

    def get_entry(self, entry_id: str) -> tuple[JournalEntry, List[JournalPosting]]:
        entry = self.db.get(JournalEntry, entry_id)
        if entry is None:
            raise EntryNotFoundError("entry not found")

        postings = self.db.execute(select(JournalPosting).where(JournalPosting.entry_id == entry_id)).scalars().all()
        return entry, postings

    def get_balance(self, account_id: str) -> tuple[str, int]:
        account = self.db.get(LedgerAccount, account_id)
        if account is None:
            raise AccountNotFoundError("account not found")

        postings = self.db.execute(
            select(JournalPosting).where(JournalPosting.account_id == account_id)
        ).scalars().all()

        balance = 0
        for posting in postings:
            if posting.direction == PostingDirection.CREDIT:
                balance += posting.amount_minor
            else:
                balance -= posting.amount_minor

        return account.currency, balance

    def reverse_entry(self, entry_id: str, reversal_external_ref: str) -> tuple[JournalEntry, List[JournalPosting]]:
        original_entry, original_postings = self.get_entry(entry_id)

        reverse_lines: List[PostingLineRequest] = []
        for posting in original_postings:
            reverse_lines.append(
                PostingLineRequest(
                    account_id=posting.account_id,
                    direction=(
                        PostingDirection.CREDIT
                        if posting.direction == PostingDirection.DEBIT
                        else PostingDirection.DEBIT
                    ),
                    amount_minor=posting.amount_minor,
                    currency=posting.currency,
                )
            )

        return self.create_entry(
            external_ref=reversal_external_ref,
            transfer_id=original_entry.transfer_id,
            entry_type=EntryType.REVERSAL,
            posting_lines=reverse_lines,
        )

    def list_entry_summaries(self) -> List[Dict[str, object]]:
        entries = self.db.execute(select(JournalEntry)).scalars().all()
        summaries: List[Dict[str, object]] = []

        for entry in entries:
            postings = self.db.execute(
                select(JournalPosting).where(JournalPosting.entry_id == entry.entry_id)
            ).scalars().all()
            debit_total = sum(
                posting.amount_minor
                for posting in postings
                if posting.direction == PostingDirection.DEBIT
            )
            currency = postings[0].currency if postings else ""
            summaries.append(
                {
                    "external_ref": entry.external_ref,
                    "amount_minor": debit_total,
                    "currency": currency,
                }
            )

        return summaries
