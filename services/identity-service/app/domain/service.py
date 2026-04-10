from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DuplicateUserError, InvalidKycTransitionError, UserNotFoundError
from app.domain.models import KycStatus, User
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
