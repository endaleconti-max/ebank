from app.domain.models import ConnectorStatus


def mock_provider_submit(external_ref: str, amount_minor: int) -> tuple[str, str]:
    del amount_minor
    if external_ref.endswith("-fail"):
        return "MOCK_REJECTED", "mock provider rejected transaction"
    return "MOCK_ACCEPTED", "mock provider accepted transaction"


def mock_provider_callback_status(requested_status: ConnectorStatus) -> ConnectorStatus:
    if requested_status in {ConnectorStatus.CONFIRMED, ConnectorStatus.FAILED, ConnectorStatus.PENDING}:
        return requested_status
    return ConnectorStatus.PENDING
