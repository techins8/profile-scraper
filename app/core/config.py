from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    DATABASE_URL: Optional[str] = "postgresql://app:password@database:5432/malt"
    OPENAI_API_KEY: str
    HTTP_TOKEN: str
    SENTRY_DSN: str | None = None
    ENVIRONMENT: str = "local"
    WORKSPACE_BASE_PATH: str = "var"
    COOKIES: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env"),
        extra="ignore",
        case_sensitive=False,
    )


config = AppConfig()
