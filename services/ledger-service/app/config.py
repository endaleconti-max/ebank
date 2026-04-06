from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEDGER_", case_sensitive=False)

    service_name: str = "ledger-service"
    database_url: str = "sqlite+pysqlite:///./ledger.db"


settings = Settings()
