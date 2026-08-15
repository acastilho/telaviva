from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.recordings.models import RecordingAccessSource, RecordingStatus


class RecordingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stream_id: UUID
    status: RecordingStatus
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    metadata: dict[str, Any]
    failure_reason: str | None
    playback_url: str | None = None
    thumbnail_url: str | None = None


class ProcessingComplete(BaseModel):
    playback_key: str = Field(min_length=1, max_length=1024)
    thumbnail_key: str = Field(min_length=1, max_length=1024)
    duration_seconds: int = Field(ge=0, le=86400)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessingFailed(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class LibraryRecordingResponse(RecordingResponse):
    title: str
    creator_name: str
    access_source: RecordingAccessSource
    progress_seconds: int
    completed: bool
    last_watched_at: datetime | None


class RecordingLibraryResponse(BaseModel):
    my_classes: list[LibraryRecordingResponse]
    continue_watching: list[LibraryRecordingResponse]
    purchased: list[LibraryRecordingResponse]
    subscriptions: list[LibraryRecordingResponse]
    history: list[LibraryRecordingResponse]


class ProgressUpdate(BaseModel):
    position_seconds: int = Field(ge=0, le=86400)


class ProgressResponse(BaseModel):
    recording_id: UUID
    position_seconds: int
    completed: bool
    updated_at: datetime
