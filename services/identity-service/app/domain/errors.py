class DomainError(Exception):
    pass


class UserNotFoundError(DomainError):
    pass


class DuplicateUserError(DomainError):
    pass


class InvalidKycTransitionError(DomainError):
    pass


class InvalidAccountTransitionError(DomainError):
    pass
