from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMPLIANCE_", case_sensitive=False)

    service_name: str = "compliance-service"
    database_url: str = "sqlite:///./compliance.db"
    # Name matching: Levenshtein distance <= this threshold triggers a POTENTIAL_MATCH
    name_match_threshold: int = 2


settings = Settings()
