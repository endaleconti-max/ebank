from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IDENTITY_", case_sensitive=False)

    service_name: str = "identity-service"
    database_url: str = "sqlite+pysqlite:///./identity.db"
    compliance_service_base_url: str = "http://localhost:8007"
    compliance_service_enabled: bool = False
    compliance_service_timeout_seconds: float = 2.0
    # Policy when compliance service is unreachable: "allow" or "deny"
    compliance_service_fallback_policy: str = "allow"


settings = Settings()
