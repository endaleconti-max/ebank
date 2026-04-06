class DomainError(Exception):
    pass


class TransferNotFoundError(DomainError):
    pass


class InvalidTransitionError(DomainError):
    pass


class DuplicateIdempotencyKeyError(DomainError):
    pass


class InvalidTransferRequestError(DomainError):
    pass


class ConnectorCallbackTargetNotFoundError(DomainError):
    pass
