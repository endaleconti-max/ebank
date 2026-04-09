from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    service_name: str = "api-gateway"
    orchestrator_base_url: str = "http://localhost:8004"
    connector_base_url: str = "http://localhost:8005"
    reconciliation_base_url: str = "http://localhost:8006"
    identity_base_url: str = "http://localhost:8001"
    alias_base_url: str = "http://localhost:8002"
    enforce_idempotency: bool = True
    enforce_authentication: bool = True
    enforce_authorization: bool = True
    cors_allowed_origins: list[str] = ["*"]


settings = Settings()
