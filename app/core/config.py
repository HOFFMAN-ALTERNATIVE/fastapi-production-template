from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "fastapi-production-template"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: SecretStr = Field(default=SecretStr("change-me"), min_length=8)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60

    cors_origins: list[str] = []

    @model_validator(mode="after")
    def _require_real_secret_outside_dev(self) -> "Settings":
        """Refuse to start staging or production with the placeholder or a short JWT secret."""
        if self.environment in ("staging", "production"):
            secret = self.jwt_secret.get_secret_value()
            if len(secret) < 32 or "change" in secret.lower():
                raise ValueError(
                    "JWT_SECRET must be at least 32 random characters in staging and production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
