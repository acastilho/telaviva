from decimal import Decimal
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TelaViva API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://telaviva:telaviva_local@localhost:5432/telaviva"
    redis_url: str = "redis://localhost:6379/0"
    api_cors_origins: list[str] = Field(default=["http://localhost:5173"])
    jwt_secret: str = "development-only-change-me-at-least-32-characters"
    jwt_issuer: str = "telaviva-api"
    access_token_minutes: int = Field(default=15, ge=1)
    refresh_token_days: int = Field(default=30, ge=1)
    password_reset_minutes: int = Field(default=30, ge=1)
    payment_provider: str = "fake"
    platform_fee_rate: Decimal = Field(default=Decimal("0.10"), ge=0, lt=1)

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if self.app_env.lower() in {"production", "prod"} and self.jwt_secret.startswith(
            "development-only"
        ):
            raise ValueError("JWT_SECRET must be configured in production")
        if self.app_env.lower() in {"production", "prod"} and self.payment_provider == "fake":
            raise ValueError("PAYMENT_PROVIDER must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
