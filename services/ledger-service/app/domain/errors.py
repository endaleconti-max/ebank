class DomainError(Exception):
    pass


class AccountNotFoundError(DomainError):
    pass


class InactiveAccountError(DomainError):
    pass


class InvariantViolationError(DomainError):
    pass


class DuplicateExternalReferenceError(DomainError):
    pass


class EntryNotFoundError(DomainError):
    pass
