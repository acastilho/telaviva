from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TelaViva API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://telaviva:telaviva_local@localhost:5432/telaviva"
    redis_url: str = "redis://localhost:6379/0"
    api_cors_origins: list[str] = Field(default=["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
