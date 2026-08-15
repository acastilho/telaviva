from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.interaction.models import InteractionKind, ModerationAction


class SettingsUpdate(BaseModel):
    chat_enabled: bool
    questions_enabled: bool
    reactions_enabled: bool


class SettingsResponse(SettingsUpdate):
    stream_id: UUID
    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    kind: InteractionKind
    content: str = Field(min_length=1, max_length=500)


class EventResponse(BaseModel):
    id: UUID
    stream_id: UUID
    user_id: UUID
    kind: InteractionKind
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ModerationCreate(BaseModel):
    user_id: UUID
    action: ModerationAction
    duration_minutes: int | None = Field(default=None, ge=1, le=10080)


class ReportCreate(BaseModel):
    event_id: UUID
    reason: str = Field(min_length=3, max_length=500)


class ReportResponse(BaseModel):
    id: UUID
    stream_id: UUID
    reporter_id: UUID
    event_id: UUID
    reason: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
