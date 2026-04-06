class DomainError(Exception):
    pass


class ConnectorNotSupportedError(DomainError):
    pass


class DuplicateExternalRefError(DomainError):
    pass


class ConnectorTransactionNotFoundError(DomainError):
    pass
