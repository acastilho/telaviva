from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.identity.models import Role, User


class DuplicateEmailError(Exception):
    pass


class IdentityRepository(Protocol):
    async def create_user(self, email: str, password_hash: str, role: Role) -> User: ...
    async def get_user_by_email(self, email: str) -> User | None: ...
    async def get_user_by_id(self, user_id: UUID) -> User | None: ...
    async def list_users(self) -> list[User]: ...
    async def store_refresh_token(
        self, token_id: UUID, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> None: ...
    async def consume_refresh_token(self, token_id: UUID, token_hash: str) -> bool: ...
    async def store_recovery_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> None: ...
    async def consume_recovery_token(self, token_hash: str, password_hash: str) -> bool: ...


def _user(record: asyncpg.Record) -> User:
    return User(
        id=record["id"], email=record["email"], password_hash=record["password_hash"],
        role=Role(record["role"]), created_at=record["created_at"]
    )


class PostgresIdentityRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def create_user(self, email: str, password_hash: str, role: Role) -> User:
        connection = await self._connect()
        try:
            record = await connection.fetchrow(
                "INSERT INTO users (id,email,password_hash,role) VALUES ($1,$2,$3,$4) "
                "RETURNING id,email,password_hash,role,created_at",
                uuid4(), email, password_hash, role.value,
            )
        except asyncpg.UniqueViolationError as error:
            raise DuplicateEmailError from error
        finally:
            await connection.close()
        assert record is not None
        return _user(record)

    async def get_user_by_email(self, email: str) -> User | None:
        connection = await self._connect()
        try:
            record = await connection.fetchrow("SELECT * FROM users WHERE email=$1", email)
            return _user(record) if record else None
        finally:
            await connection.close()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        connection = await self._connect()
        try:
            record = await connection.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
            return _user(record) if record else None
        finally:
            await connection.close()

    async def list_users(self) -> list[User]:
        connection = await self._connect()
        try:
            records = await connection.fetch("SELECT * FROM users ORDER BY created_at")
            return [_user(record) for record in records]
        finally:
            await connection.close()

    async def store_refresh_token(
        self, token_id: UUID, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        connection = await self._connect()
        try:
            await connection.execute(
                "INSERT INTO refresh_tokens (id,user_id,token_hash,expires_at) "
                "VALUES ($1,$2,$3,$4)",
                token_id, user_id, token_hash, expires_at,
            )
        finally:
            await connection.close()

    async def consume_refresh_token(self, token_id: UUID, token_hash: str) -> bool:
        connection = await self._connect()
        try:
            result = await connection.execute(
                "UPDATE refresh_tokens SET revoked_at=now() WHERE id=$1 AND token_hash=$2 "
                "AND revoked_at IS NULL AND expires_at>now()", token_id, token_hash,
            )
            return result == "UPDATE 1"
        finally:
            await connection.close()

    async def store_recovery_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        connection = await self._connect()
        try:
            async with connection.transaction():
                await connection.execute(
                    "UPDATE password_reset_tokens SET used_at=now() "
                    "WHERE user_id=$1 AND used_at IS NULL",
                    user_id,
                )
                await connection.execute(
                    "INSERT INTO password_reset_tokens (id,user_id,token_hash,expires_at) "
                    "VALUES ($1,$2,$3,$4)",
                    uuid4(), user_id, token_hash, expires_at,
                )
        finally:
            await connection.close()

    async def consume_recovery_token(self, token_hash: str, password_hash: str) -> bool:
        connection = await self._connect()
        try:
            async with connection.transaction():
                user_id = await connection.fetchval(
                    "UPDATE password_reset_tokens SET used_at=now() WHERE token_hash=$1 "
                    "AND used_at IS NULL AND expires_at>now() RETURNING user_id", token_hash,
                )
                if user_id is None:
                    return False
                await connection.execute(
                    "UPDATE users SET password_hash=$1 WHERE id=$2", password_hash, user_id
                )
                await connection.execute(
                    "UPDATE refresh_tokens SET revoked_at=now() "
                    "WHERE user_id=$1 AND revoked_at IS NULL",
                    user_id,
                )
                return True
        finally:
            await connection.close()
