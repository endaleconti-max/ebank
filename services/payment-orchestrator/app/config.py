from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
