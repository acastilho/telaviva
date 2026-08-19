from decimal import Decimal
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Instituto Tela Viva API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://telaviva:telaviva_local@localhost:5432/telaviva"
    redis_url: str = "redis://localhost:6379/0"
    api_cors_origins: list[str] = Field(default=["http://localhost:5173"])
    rate_limit_requests: int = Field(default=120, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    auth_rate_limit_requests: int = Field(default=20, ge=1, le=1000)
    max_request_body_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    jwt_secret: str = "development-only-change-me-at-least-32-characters"
    jwt_issuer: str = "telaviva-api"
    access_token_minutes: int = Field(default=15, ge=1)
    refresh_token_days: int = Field(default=30, ge=1)
    password_reset_minutes: int = Field(default=30, ge=1)
    payment_provider: str = "fake"
    platform_fee_rate: Decimal = Field(default=Decimal("0.10"), ge=0, lt=1)
    recording_bucket: str = "telaviva-recordings"
    recording_s3_endpoint_url: str | None = None
    recording_s3_region: str = "us-east-1"
    recording_url_ttl_seconds: int = Field(default=900, ge=60, le=86400)

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
        if any(origin == "*" for origin in self.api_cors_origins):
            raise ValueError("API_CORS_ORIGINS cannot contain a wildcard when credentials are enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
