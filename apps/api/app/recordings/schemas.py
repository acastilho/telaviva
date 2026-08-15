from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.recordings.models import RecordingStatus


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
