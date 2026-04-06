from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RECON_", case_sensitive=False)

    service_name: str = "reconciliation-service"
    database_url: str = "sqlite+pysqlite:///./reconciliation.db"
    source_mode: str = "db"
    ledger_service_base_url: str = "http://localhost:8003"
    connector_service_base_url: str = "http://localhost:8005"
    ledger_db_path: str = "../ledger-service/ledger.db"
    connector_db_path: str = "../connector-gateway/connector.db"


settings = Settings()
