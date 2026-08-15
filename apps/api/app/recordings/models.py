from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RecordingStatus(StrEnum):
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class RecordingAccessSource(StrEnum):
    PURCHASE = "PURCHASE"
    SUBSCRIPTION = "SUBSCRIPTION"
    OWNER = "OWNER"
    INCLUDED = "INCLUDED"


@dataclass(frozen=True)
class Recording:
    id: UUID
    stream_id: UUID
    status: RecordingStatus
    source_key: str
    playback_key: str | None
    thumbnail_key: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    metadata: dict[str, object]
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class LibraryRecording:
    recording: Recording
    title: str
    creator_name: str
    access_source: RecordingAccessSource
    progress_seconds: int
    completed: bool
    last_watched_at: datetime | None


@dataclass(frozen=True)
class ViewingProgress:
    recording_id: UUID
    user_id: UUID
    position_seconds: int
    completed: bool
    updated_at: datetime
