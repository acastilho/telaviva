from typing import Protocol

import asyncpg
from redis.asyncio import Redis

from app.config import Settings


class HealthChecker(Protocol):
    async def check(self) -> dict[str, str]: ...


class InfrastructureHealthChecker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check(self) -> dict[str, str]:
        database_url = self._settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        connection = await asyncpg.connect(database_url, timeout=2)
        try:
            await connection.execute("SELECT 1")
        finally:
            await connection.close()

        redis = Redis.from_url(self._settings.redis_url, socket_connect_timeout=2)
        try:
            await redis.ping()
        finally:
            await redis.aclose()

        return {"database": "up", "redis": "up"}
