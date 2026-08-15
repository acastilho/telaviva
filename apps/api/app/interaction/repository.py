from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.interaction.models import (
    InteractionEvent,
    InteractionKind,
    InteractionSettings,
    ModerationAction,
    Report,
)


class StreamNotFoundError(Exception):
    pass


class EventNotFoundError(Exception):
    pass


class InteractionRepository(Protocol):
    async def stream_creator(self, stream_id: UUID) -> UUID | None: ...
    async def get_settings(self, stream_id: UUID) -> InteractionSettings | None: ...
    async def update_settings(self, stream_id: UUID, values: InteractionSettings) -> InteractionSettings: ...
    async def restriction(self, stream_id: UUID, user_id: UUID) -> ModerationAction | None: ...
    async def add_event(self, stream_id: UUID, user_id: UUID, kind: InteractionKind, content: str) -> InteractionEvent: ...
    async def recent_events(self, stream_id: UUID, limit: int) -> list[InteractionEvent]: ...
    async def moderate(self, stream_id: UUID, user_id: UUID, moderator_id: UUID, action: ModerationAction, duration_minutes: int | None) -> None: ...
    async def report(self, stream_id: UUID, reporter_id: UUID, event_id: UUID, reason: str) -> Report: ...


def _event(record: asyncpg.Record) -> InteractionEvent:
    return InteractionEvent(record["id"], record["stream_id"], record["user_id"], InteractionKind(record["kind"]), record["content"], record["created_at"])


class PostgresInteractionRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def stream_creator(self, stream_id: UUID) -> UUID | None:
        connection = await self._connect()
        try:
            return await connection.fetchval("SELECT creator_id FROM scheduled_streams WHERE id=$1", stream_id)
        finally:
            await connection.close()

    async def get_settings(self, stream_id: UUID) -> InteractionSettings | None:
        connection = await self._connect()
        try:
            record = await connection.fetchrow("SELECT s.id AS stream_id, COALESCE(i.chat_enabled,true) AS chat_enabled, COALESCE(i.questions_enabled,true) AS questions_enabled, COALESCE(i.reactions_enabled,true) AS reactions_enabled FROM scheduled_streams s LEFT JOIN stream_interaction_settings i ON i.stream_id=s.id WHERE s.id=$1", stream_id)
            return InteractionSettings(**dict(record)) if record else None
        finally:
            await connection.close()

    async def update_settings(self, stream_id: UUID, values: InteractionSettings) -> InteractionSettings:
        connection = await self._connect()
        try:
            record = await connection.fetchrow("INSERT INTO stream_interaction_settings (stream_id,chat_enabled,questions_enabled,reactions_enabled) VALUES ($1,$2,$3,$4) ON CONFLICT (stream_id) DO UPDATE SET chat_enabled=$2,questions_enabled=$3,reactions_enabled=$4 RETURNING *", stream_id, values.chat_enabled, values.questions_enabled, values.reactions_enabled)
            if record is None:
                raise StreamNotFoundError
            return InteractionSettings(record["stream_id"], record["chat_enabled"], record["questions_enabled"], record["reactions_enabled"])
        finally:
            await connection.close()

    async def restriction(self, stream_id: UUID, user_id: UUID) -> ModerationAction | None:
        connection = await self._connect()
        try:
            value = await connection.fetchval("SELECT action FROM stream_moderation WHERE stream_id=$1 AND user_id=$2 AND (expires_at IS NULL OR expires_at>now()) ORDER BY CASE action WHEN 'ban' THEN 0 ELSE 1 END LIMIT 1", stream_id, user_id)
            return ModerationAction(value) if value else None
        finally:
            await connection.close()

    async def add_event(self, stream_id: UUID, user_id: UUID, kind: InteractionKind, content: str) -> InteractionEvent:
        connection = await self._connect()
        try:
            record = await connection.fetchrow("INSERT INTO stream_events (id,stream_id,user_id,kind,content) VALUES ($1,$2,$3,$4,$5) RETURNING *", uuid4(), stream_id, user_id, kind.value, content)
            assert record is not None
            return _event(record)
        finally:
            await connection.close()

    async def recent_events(self, stream_id: UUID, limit: int) -> list[InteractionEvent]:
        connection = await self._connect()
        try:
            records = await connection.fetch("SELECT * FROM (SELECT * FROM stream_events WHERE stream_id=$1 ORDER BY created_at DESC LIMIT $2) e ORDER BY created_at", stream_id, limit)
            return [_event(item) for item in records]
        finally:
            await connection.close()

    async def moderate(self, stream_id: UUID, user_id: UUID, moderator_id: UUID, action: ModerationAction, duration_minutes: int | None) -> None:
        expires_at = datetime.now(UTC) + timedelta(minutes=duration_minutes) if duration_minutes else None
        connection = await self._connect()
        try:
            await connection.execute("INSERT INTO stream_moderation (id,stream_id,user_id,moderator_id,action,expires_at) VALUES ($1,$2,$3,$4,$5,$6)", uuid4(), stream_id, user_id, moderator_id, action.value, expires_at)
        finally:
            await connection.close()

    async def report(self, stream_id: UUID, reporter_id: UUID, event_id: UUID, reason: str) -> Report:
        connection = await self._connect()
        try:
            report_id = uuid4()
            record = await connection.fetchrow("INSERT INTO interaction_reports (id,stream_id,reporter_id,event_id,reason) SELECT $1,$2,$3,id,$5 FROM stream_events WHERE id=$4 AND stream_id=$2 RETURNING *", report_id, stream_id, reporter_id, event_id, reason)
            if record is None:
                raise EventNotFoundError
            return Report(record["id"], record["stream_id"], record["reporter_id"], record["event_id"], record["reason"], record["created_at"])
        finally:
            await connection.close()
