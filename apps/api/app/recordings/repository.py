import json
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.recordings.models import Recording, RecordingStatus


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
