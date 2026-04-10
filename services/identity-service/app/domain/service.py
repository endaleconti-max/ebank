from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DuplicateUserError, InvalidAccountTransitionError, InvalidKycTransitionError, UserNotFoundError
from app.domain.models import AccountAuditLog, AccountStatus, KycStatus, User
from app.domain.compliance_client import screen_subject
from app.config import settings


class IdentityService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, full_name: str, country_code: str, email: str) -> User:
        existing = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            raise DuplicateUserError("email already exists")

        user = User(full_name=full_name, country_code=country_code.upper(), email=email.lower())
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, user_id: str) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise UserNotFoundError("user not found")
        return user

    def submit_kyc(self, user_id: str) -> User:
        user = self.get_user(user_id)
        if user.kyc_status not in {KycStatus.NOT_STARTED, KycStatus.REJECTED}:
            raise InvalidKycTransitionError("kyc submit transition invalid")

        user.kyc_status = KycStatus.SUBMITTED
        self.db.commit()
        self.db.refresh(user)
        return user

    def decide_kyc(self, user_id: str, decision: KycStatus) -> User:
        if decision not in {KycStatus.APPROVED, KycStatus.REJECTED}:
            raise InvalidKycTransitionError("decision must be APPROVED or REJECTED")

        user = self.get_user(user_id)
        if user.kyc_status != KycStatus.SUBMITTED:
            raise InvalidKycTransitionError("kyc decision transition invalid")

        # Run sanctions screening when approving — an operator decision cannot
        # override a confirmed watchlist hit.
        if decision == KycStatus.APPROVED:
            screen_result = screen_subject(
                subject_id=user_id,
                subject_type="user",
                name=user.full_name,
                caller_id="identity-service",
            )
            if screen_result is not None:
                screen_decision, _, _ = screen_result
                if screen_decision == "hit":
                    # Hard block: sanctions hit overrides operator approval
                    decision = KycStatus.REJECTED
            else:
                # Service unavailable: apply configured fallback policy
                if settings.compliance_service_fallback_policy == "deny":
                    decision = KycStatus.REJECTED

        user.kyc_status = decision
        self.db.commit()
        self.db.refresh(user)
        return user

    # ── Account lifecycle ─────────────────────────────────────────────────────

    def _transition_account_status(
        self,
        user_id: str,
        allowed_from: set,
        to_status: AccountStatus,
        reason: str,
        actor_id: str,
    ) -> User:
        user = self.get_user(user_id)
        if user.account_status not in allowed_from:
            raise InvalidAccountTransitionError(
                f"cannot transition from {user.account_status} to {to_status}"
            )
        from_status = user.account_status
        user.account_status = to_status
        log = AccountAuditLog(
            user_id=user_id,
            from_status=from_status.value,
            to_status=to_status.value,
            reason=reason,
            actor_id=actor_id,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(user)
        return user

    def suspend_account(self, user_id: str, reason: str, actor_id: str) -> User:
        return self._transition_account_status(
            user_id=user_id,
            allowed_from={AccountStatus.ACTIVE},
            to_status=AccountStatus.SUSPENDED,
            reason=reason,
            actor_id=actor_id,
        )

    def reinstate_account(self, user_id: str, reason: str, actor_id: str) -> User:
        return self._transition_account_status(
            user_id=user_id,
            allowed_from={AccountStatus.SUSPENDED},
            to_status=AccountStatus.ACTIVE,
            reason=reason,
            actor_id=actor_id,
        )

    def close_account(self, user_id: str, reason: str, actor_id: str) -> User:
        return self._transition_account_status(
            user_id=user_id,
            allowed_from={AccountStatus.ACTIVE, AccountStatus.SUSPENDED},
            to_status=AccountStatus.CLOSED,
            reason=reason,
            actor_id=actor_id,
        )

    def list_account_audit_log(self, user_id: str) -> list:
        rows = (
            self.db.execute(
                select(AccountAuditLog)
                .where(AccountAuditLog.user_id == user_id)
                .order_by(AccountAuditLog.created_at)
            )
            .scalars()
            .all()
        )
        return list(rows)
