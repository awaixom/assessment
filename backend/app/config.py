from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://worklog:worklog@localhost:5432/worklog"
    payout_simulate_failure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()
