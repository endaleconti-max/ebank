from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALIAS_", case_sensitive=False)

    service_name: str = "alias-service"
    database_url: str = "sqlite+pysqlite:///./alias.db"


settings = Settings()
