from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    service_name: str = "risk-service"
    database_url: str = "sqlite:///./risk.db"
    # Default rule limits used when no DB rules are configured
    default_amount_limit_minor: int = 1_000_000  # 10 000.00 in minor units


settings = Settings()
