from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IDENTITY_", case_sensitive=False)

    service_name: str = "identity-service"
    database_url: str = "sqlite+pysqlite:///./identity.db"


settings = Settings()
