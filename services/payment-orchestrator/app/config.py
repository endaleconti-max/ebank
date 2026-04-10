from pydantic_settings import BaseSettings, SettingsConfigDict


class TransferLimitTier:
    """Transfer limits per KYC status tier."""
    def __init__(self, kyc_status: str, single_transfer_limit_minor: int, daily_limit_minor: int):
        self.kyc_status = kyc_status
        self.single_transfer_limit_minor = single_transfer_limit_minor
        self.daily_limit_minor = daily_limit_minor


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCHESTRATOR_", case_sensitive=False)

    service_name: str = "payment-orchestrator"
    database_url: str = "sqlite+pysqlite:///./orchestrator.db"
    risk_amount_limit_minor: int = 100_000
    connector_submission_enabled: bool = True
    connector_submission_mode: str = "http"
    connector_base_url: str = "http://localhost:8005"
    connector_id: str = "mock-bank-a"
    connector_destination: str = "acct-orchestrator-default"
    ledger_base_url: str = "http://localhost:8003"
    ledger_posting_enabled: bool = False
    risk_service_base_url: str = "http://localhost:8006"
    risk_service_enabled: bool = False
    risk_service_timeout_seconds: float = 2.0
    identity_service_base_url: str = "http://localhost:8001"
    identity_service_enabled: bool = False
    identity_service_timeout_seconds: float = 2.0
    # Policy when identity-service unavailable: "allow" or "deny"
    identity_service_fallback_policy: str = "allow"
    alias_service_base_url: str = "http://localhost:8002"
    alias_service_enabled: bool = False
    alias_service_timeout_seconds: float = 2.0
    # Policy when alias-service unavailable: "allow" or "deny"
    alias_service_fallback_policy: str = "allow"
    # Transfer limits by KYC status (minor currency units)
    transfer_limits_by_kyc_status: dict = {
        "NOT_STARTED": {"single_minor": 10_000, "daily_minor": 20_000},
        "SUBMITTED": {"single_minor": 10_000, "daily_minor": 20_000},
        "APPROVED": {"single_minor": 500_000, "daily_minor": 2_000_000},
        "REJECTED": {"single_minor": 0, "daily_minor": 0},
    }
    transfer_limits_enabled: bool = True


settings = Settings()
