class DomainError(Exception):
    pass


class ReconciliationRunNotFoundError(DomainError):
    pass


class SourceDatabaseError(DomainError):
    pass
