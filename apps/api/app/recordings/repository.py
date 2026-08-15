import json
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.recordings.models import (
    LibraryRecording,
    Recording,
    RecordingAccessSource,
    RecordingStatus,
    ViewingProgress,
)


class StreamNotFoundError(Exception):
    pass


class InvalidRecordingTransitionError(Exception):
    pass


class RecordingRepository(Protocol):
    async def stream_creator(self, stream_id: UUID) -> UUID | None: ...
    async def get_for_stream(self, stream_id: UUID) -> Recording | None: ...
    async def start(self, stream_id: UUID, source_key: str) -> Recording: ...
    async def stop(self, stream_id: UUID) -> Recording: ...
    async def complete(
        self, recording_id: UUID, playback_key: str, thumbnail_key: str,
        duration_seconds: int, metadata: dict[str, object],
    ) -> Recording: ...
    async def fail(self, recording_id: UUID, reason: str) -> Recording: ...
    async def get(self, recording_id: UUID) -> Recording | None: ...
    async def list_library(self, user_id: UUID) -> list[LibraryRecording]: ...
    async def save_progress(
        self, recording_id: UUID, user_id: UUID, position_seconds: int
    ) -> ViewingProgress: ...


def _recording(row: asyncpg.Record) -> Recording:
    metadata = row["metadata"]
    return Recording(
        row["id"], row["stream_id"], RecordingStatus(row["status"]), row["source_key"],
        row["playback_key"], row["thumbnail_key"], row["started_at"], row["ended_at"],
        row["duration_seconds"],
        json.loads(metadata) if isinstance(metadata, str) else dict(metadata),
        row["failure_reason"], row["created_at"], row["updated_at"],
    )


class PostgresRecordingRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def stream_creator(self, stream_id: UUID) -> UUID | None:
        connection = await self._connect()
        try:
            return await connection.fetchval(
                "SELECT creator_id FROM scheduled_streams WHERE id=$1", stream_id
            )
        finally:
            await connection.close()

    async def get_for_stream(self, stream_id: UUID) -> Recording | None:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "SELECT * FROM recordings WHERE stream_id=$1", stream_id
            )
            return _recording(row) if row else None
        finally:
            await connection.close()

    async def get(self, recording_id: UUID) -> Recording | None:
        connection = await self._connect()
        try:
            row = await connection.fetchrow("SELECT * FROM recordings WHERE id=$1", recording_id)
            return _recording(row) if row else None
        finally:
            await connection.close()

    async def list_library(self, user_id: UUID) -> list[LibraryRecording]:
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                "SELECT r.*,s.title,cp.name creator_name,vp.position_seconds,vp.completed,"
                "vp.updated_at last_watched_at,CASE WHEN s.creator_id=$1 THEN 'OWNER' "
                "WHEN se.id IS NOT NULL THEN 'PURCHASE' WHEN ce.id IS NOT NULL THEN 'SUBSCRIPTION' "
                "ELSE 'INCLUDED' END access_source FROM recordings r "
                "JOIN scheduled_streams s ON s.id=r.stream_id "
                "JOIN creator_profiles cp ON cp.user_id=s.creator_id "
                "LEFT JOIN viewing_progress vp ON vp.recording_id=r.id AND vp.user_id=$1 "
                "LEFT JOIN entitlements se ON se.user_id=$1 AND se.kind='STREAM' "
                "AND se.resource_id=s.id AND se.revoked_at IS NULL AND se.starts_at<=now() "
                "AND (se.expires_at IS NULL OR se.expires_at>now()) "
                "LEFT JOIN entitlements ce ON ce.user_id=$1 AND ce.kind='CREATOR_SUBSCRIPTION' "
                "AND ce.resource_id=s.creator_id AND ce.revoked_at IS NULL AND ce.starts_at<=now() "
                "AND (ce.expires_at IS NULL OR ce.expires_at>now()) "
                "LEFT JOIN stream_invites i ON i.stream_id=s.id AND i.user_id=$1 "
                "WHERE r.status='READY' AND (s.creator_id=$1 "
                "OR (s.access_type='FREE' AND vp.recording_id IS NOT NULL) "
                "OR (s.access_type='PRIVATE' AND i.user_id IS NOT NULL) "
                "OR (s.access_type='PAID' AND se.id IS NOT NULL) "
                "OR (s.access_type='SUBSCRIBERS' AND ce.id IS NOT NULL)) "
                "ORDER BY COALESCE(vp.updated_at,r.ended_at,r.created_at) DESC",
                user_id,
            )
            return [LibraryRecording(
                _recording(row), row["title"], row["creator_name"],
                RecordingAccessSource(row["access_source"]), row["position_seconds"] or 0,
                row["completed"] or False, row["last_watched_at"],
            ) for row in rows]
        finally:
            await connection.close()

    async def save_progress(
        self, recording_id: UUID, user_id: UUID, position_seconds: int
    ) -> ViewingProgress:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "INSERT INTO viewing_progress (recording_id,user_id,position_seconds,completed) "
                "SELECT id,$2,LEAST($3,duration_seconds),"
                "CASE WHEN duration_seconds=0 THEN true ELSE $3::numeric/duration_seconds>=0.95 END "
                "FROM recordings WHERE id=$1 AND status='READY' "
                "ON CONFLICT (recording_id,user_id) DO UPDATE SET "
                "position_seconds=EXCLUDED.position_seconds,completed=EXCLUDED.completed,updated_at=now() "
                "RETURNING recording_id,user_id,position_seconds,completed,updated_at",
                recording_id, user_id, position_seconds,
            )
            if row is None:
                raise InvalidRecordingTransitionError
            return ViewingProgress(
                row["recording_id"], row["user_id"], row["position_seconds"],
                row["completed"], row["updated_at"],
            )
        finally:
            await connection.close()

    async def start(self, stream_id: UUID, source_key: str) -> Recording:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "INSERT INTO recordings (id,stream_id,status,source_key) "
                "SELECT $1,id,'RECORDING',$3 FROM scheduled_streams WHERE id=$2 "
                "ON CONFLICT (stream_id) DO NOTHING RETURNING *", uuid4(), stream_id, source_key,
            )
            if row is None:
                if not await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM scheduled_streams WHERE id=$1)", stream_id
                ):
                    raise StreamNotFoundError
                existing = await self.get_for_stream(stream_id)
                if existing is None:
                    raise InvalidRecordingTransitionError
                return existing
            return _recording(row)
        finally:
            await connection.close()

    async def stop(self, stream_id: UUID) -> Recording:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "UPDATE recordings SET status='PROCESSING',ended_at=now(),updated_at=now() "
                "WHERE stream_id=$1 AND status='RECORDING' RETURNING *", stream_id,
            )
            if row is None:
                raise InvalidRecordingTransitionError
            return _recording(row)
        finally:
            await connection.close()

    async def complete(self, recording_id: UUID, playback_key: str, thumbnail_key: str,
                       duration_seconds: int, metadata: dict[str, object]) -> Recording:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "UPDATE recordings SET status='READY',playback_key=$2,thumbnail_key=$3,"
                "duration_seconds=$4,metadata=$5,updated_at=now() "
                "WHERE id=$1 AND status='PROCESSING' RETURNING *",
                recording_id, playback_key, thumbnail_key, duration_seconds, json.dumps(metadata),
            )
            if row is None:
                raise InvalidRecordingTransitionError
            return _recording(row)
        finally:
            await connection.close()

    async def fail(self, recording_id: UUID, reason: str) -> Recording:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "UPDATE recordings SET status='FAILED',failure_reason=$2,updated_at=now(),"
                "ended_at=COALESCE(ended_at,now()) WHERE id=$1 "
                "AND status IN ('RECORDING','PROCESSING') "
                "RETURNING *", recording_id, reason,
            )
            if row is None:
                raise InvalidRecordingTransitionError
            return _recording(row)
        finally:
            await connection.close()
