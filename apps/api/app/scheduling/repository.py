import json
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.scheduling.models import (
    AccessType,
    Level,
    Notification,
    NotificationKind,
    ScheduledStream,
)


class UnknownCategoryError(Exception):
    pass


class StreamNotFoundError(Exception):
    pass


class InvalidReminderTimeError(Exception):
    pass


class SchedulingRepository(Protocol):
    async def create_stream(self, creator_id: UUID, **values: object) -> ScheduledStream: ...
    async def list_streams(self, *, creator_id: UUID | None, starts_after: datetime) -> list[ScheduledStream]: ...
    async def list_active_streams(self) -> list[ScheduledStream]: ...
    async def activate_stream(self, stream_id: UUID, creator_id: UUID, room_id: str, started_at: datetime) -> ScheduledStream: ...
    async def finish_stream(self, stream_id: UUID, creator_id: UUID, ended_at: datetime) -> ScheduledStream: ...
    async def follow(self, user_id: UUID, creator_id: UUID) -> None: ...
    async def unfollow(self, user_id: UUID, creator_id: UUID) -> None: ...
    async def list_agenda(self, user_id: UUID, starts_after: datetime) -> list[ScheduledStream]: ...
    async def add_reminder(self, user_id: UUID, stream_id: UUID, minutes_before: int) -> datetime: ...
    async def remove_reminder(self, user_id: UUID, stream_id: UUID) -> None: ...
    async def list_notifications(self, user_id: UUID, unread_only: bool) -> list[Notification]: ...
    async def mark_notification_read(self, user_id: UUID, notification_id: UUID) -> bool: ...


def _stream(record: asyncpg.Record) -> ScheduledStream:
    return ScheduledStream(
        id=record["id"], creator_id=record["creator_id"], title=record["title"],
        description=record["description"], objective=record["objective"],
        starts_at=record["starts_at"],
        estimated_duration_minutes=record["estimated_duration_minutes"],
        category_id=record["category_id"], level=Level(record["level"]),
        price=record["price"], access_type=AccessType(record["access_type"]),
        created_at=record["created_at"], live_started_at=record["live_started_at"],
        live_ended_at=record["live_ended_at"], live_room_id=record["live_room_id"],
    )


def _notification(record: asyncpg.Record) -> Notification:
    data = record["data"]
    return Notification(
        id=record["id"], user_id=record["user_id"], kind=NotificationKind(record["kind"]),
        title=record["title"], body=record["body"],
        data=json.loads(data) if isinstance(data, str) else dict(data),
        created_at=record["created_at"], read_at=record["read_at"],
    )


class PostgresSchedulingRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def create_stream(self, creator_id: UUID, **values: object) -> ScheduledStream:
        connection = await self._connect()
        try:
            async with connection.transaction():
                if not await connection.fetchval("SELECT EXISTS(SELECT 1 FROM categories WHERE id=$1)", values["category_id"]):
                    raise UnknownCategoryError
                stream_id = uuid4()
                record = await connection.fetchrow(
                    "INSERT INTO scheduled_streams (id,creator_id,title,description,objective,starts_at,estimated_duration_minutes,category_id,level,price,access_type) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *",
                    stream_id, creator_id, values["title"], values["description"], values["objective"],
                    values["starts_at"], values["estimated_duration_minutes"], values["category_id"],
                    str(values["level"]), values["price"], str(values["access_type"]),
                )
                await connection.execute(
                    "INSERT INTO notifications (id,user_id,kind,title,body,data) SELECT gen_random_uuid(),f.follower_id,'STREAM_SCHEDULED',$2,$3,jsonb_build_object('stream_id',$1::text,'creator_id',$4::text) FROM creator_follows f WHERE f.creator_id=$4",
                    stream_id, "Nova aula agendada", str(values["title"]), creator_id,
                )
                assert record is not None
                return _stream(record)
        finally:
            await connection.close()

    async def list_streams(self, *, creator_id: UUID | None, starts_after: datetime) -> list[ScheduledStream]:
        connection = await self._connect()
        try:
            records = await connection.fetch(
                "SELECT * FROM scheduled_streams WHERE starts_at >= $1 AND ($2::uuid IS NULL OR creator_id=$2) ORDER BY starts_at,id",
                starts_after, creator_id,
            )
            return [_stream(record) for record in records]
        finally:
            await connection.close()

    async def list_active_streams(self) -> list[ScheduledStream]:
        connection = await self._connect()
        try:
            records = await connection.fetch(
                "SELECT * FROM scheduled_streams WHERE live_started_at IS NOT NULL AND live_ended_at IS NULL AND live_room_id IS NOT NULL ORDER BY live_started_at DESC,id"
            )
            return [_stream(record) for record in records]
        finally:
            await connection.close()

    async def activate_stream(self, stream_id: UUID, creator_id: UUID, room_id: str, started_at: datetime) -> ScheduledStream:
        connection = await self._connect()
        try:
            record = await connection.fetchrow(
                "UPDATE scheduled_streams SET live_started_at=$3,live_ended_at=NULL,live_room_id=$4 WHERE id=$1 AND creator_id=$2 RETURNING *",
                stream_id, creator_id, started_at, room_id,
            )
            if record is None:
                raise StreamNotFoundError
            return _stream(record)
        finally:
            await connection.close()

    async def finish_stream(self, stream_id: UUID, creator_id: UUID, ended_at: datetime) -> ScheduledStream:
        connection = await self._connect()
        try:
            record = await connection.fetchrow(
                "UPDATE scheduled_streams SET live_ended_at=$3 WHERE id=$1 AND creator_id=$2 AND live_started_at IS NOT NULL AND live_ended_at IS NULL RETURNING *",
                stream_id, creator_id, ended_at,
            )
            if record is None:
                raise StreamNotFoundError
            return _stream(record)
        finally:
            await connection.close()

    async def follow(self, user_id: UUID, creator_id: UUID) -> None:
        connection = await self._connect()
        try:
            result = await connection.execute(
                "INSERT INTO creator_follows (follower_id,creator_id) SELECT $1,$2 WHERE EXISTS (SELECT 1 FROM creator_profiles WHERE user_id=$2) ON CONFLICT DO NOTHING",
                user_id, creator_id,
            )
            if result == "INSERT 0 0":
                exists = await connection.fetchval("SELECT EXISTS(SELECT 1 FROM creator_profiles WHERE user_id=$1)", creator_id)
                if not exists:
                    raise StreamNotFoundError
        finally:
            await connection.close()

    async def unfollow(self, user_id: UUID, creator_id: UUID) -> None:
        connection = await self._connect()
        try:
            await connection.execute("DELETE FROM creator_follows WHERE follower_id=$1 AND creator_id=$2", user_id, creator_id)
        finally:
            await connection.close()

    async def list_agenda(self, user_id: UUID, starts_after: datetime) -> list[ScheduledStream]:
        connection = await self._connect()
        try:
            records = await connection.fetch(
                "SELECT DISTINCT s.* FROM scheduled_streams s LEFT JOIN creator_follows f ON f.creator_id=s.creator_id AND f.follower_id=$1 LEFT JOIN stream_reminders r ON r.stream_id=s.id AND r.user_id=$1 WHERE s.starts_at >= $2 AND (f.follower_id IS NOT NULL OR r.user_id IS NOT NULL) ORDER BY s.starts_at,s.id",
                user_id, starts_after,
            )
            return [_stream(record) for record in records]
        finally:
            await connection.close()

    async def add_reminder(self, user_id: UUID, stream_id: UUID, minutes_before: int) -> datetime:
        connection = await self._connect()
        try:
            notify_at = await connection.fetchval(
                "INSERT INTO stream_reminders (user_id,stream_id,notify_at) SELECT $1,id,starts_at-make_interval(mins => $3) FROM scheduled_streams WHERE id=$2 AND starts_at-make_interval(mins => $3) > now() ON CONFLICT (user_id,stream_id) DO UPDATE SET notify_at=EXCLUDED.notify_at,delivered_at=NULL RETURNING notify_at",
                user_id, stream_id, minutes_before,
            )
            if notify_at is None:
                exists = await connection.fetchval("SELECT EXISTS(SELECT 1 FROM scheduled_streams WHERE id=$1)", stream_id)
                if not exists:
                    raise StreamNotFoundError
                raise InvalidReminderTimeError
            return notify_at
        finally:
            await connection.close()

    async def remove_reminder(self, user_id: UUID, stream_id: UUID) -> None:
        connection = await self._connect()
        try:
            await connection.execute("DELETE FROM stream_reminders WHERE user_id=$1 AND stream_id=$2", user_id, stream_id)
        finally:
            await connection.close()

    async def list_notifications(self, user_id: UUID, unread_only: bool) -> list[Notification]:
        connection = await self._connect()
        try:
            async with connection.transaction():
                await connection.execute(
                    "WITH due AS (UPDATE stream_reminders r SET delivered_at=now() FROM scheduled_streams s WHERE r.stream_id=s.id AND r.user_id=$1 AND r.delivered_at IS NULL AND r.notify_at <= now() RETURNING r.user_id,s.id,s.title) INSERT INTO notifications (id,user_id,kind,title,body,data) SELECT gen_random_uuid(),user_id,'STREAM_REMINDER','A aula começa em breve',title,jsonb_build_object('stream_id',id::text) FROM due",
                    user_id,
                )
                records = await connection.fetch(
                    "SELECT * FROM notifications WHERE user_id=$1 AND (NOT $2 OR read_at IS NULL) ORDER BY created_at DESC,id DESC",
                    user_id, unread_only,
                )
                return [_notification(record) for record in records]
        finally:
            await connection.close()

    async def mark_notification_read(self, user_id: UUID, notification_id: UUID) -> bool:
        connection = await self._connect()
        try:
            result = await connection.execute("UPDATE notifications SET read_at=COALESCE(read_at,now()) WHERE id=$1 AND user_id=$2", notification_id, user_id)
            return result != "UPDATE 0"
        finally:
            await connection.close()
