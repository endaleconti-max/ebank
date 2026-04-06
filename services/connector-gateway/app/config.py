from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNECTOR_", case_sensitive=False)

    service_name: str = "connector-gateway"
    database_url: str = "sqlite+pysqlite:///./connector.db"
    callback_forward_enabled: bool = False
    callback_forward_url: str = "http://localhost:8000/v1/transfers/callbacks/connector"


settings = Settings()
