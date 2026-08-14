from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """
    Validated application configuration.

    Environment variables use the DETECTIVE_ prefix. For example:

        DETECTIVE_ENVIRONMENT=production
        DETECTIVE_DEBUG=false
        DETECTIVE_PORT=8000
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DETECTIVE_",
        case_sensitive=False,
        extra="ignore",
    )

    application_name: str = Field(
        default="AI Detective API",
        min_length=1,
        max_length=100,
    )
    application_version: str = Field(
        default="0.1.0",
        min_length=1,
        max_length=50,
    )

    environment: Environment = "local"
    debug: bool = False

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65_535)
    log_level: LogLevel = "INFO"

    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = True

    @model_validator(mode="after")
    def validate_environment_rules(self) -> Self:
        if self.environment in {"staging", "production"} and self.debug:
            raise ValueError("debug must be disabled in staging and production")

        if not self.api_v1_prefix.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")

        if self.api_v1_prefix.endswith("/"):
            raise ValueError("api_v1_prefix must not end with '/'")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the process-wide settings instance.

    Settings are immutable by convention after startup. Caching prevents
    repeatedly reading and parsing environment variables during requests.
    """

    return Settings()
