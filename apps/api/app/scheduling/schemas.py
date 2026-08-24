from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.scheduling.models import AccessType, Level, NotificationKind


class StreamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    objective: str = Field(min_length=1, max_length=1000)
    starts_at: datetime
    estimated_duration_minutes: int = Field(ge=5, le=720)
    category_id: UUID
    level: Level
    price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    access_type: AccessType = AccessType.FREE

    @field_validator("title", "objective")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("starts_at")
    @classmethod
    def future_aware_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone is required")
        if value <= datetime.now(UTC):
            raise ValueError("must be in the future")
        return value

    @model_validator(mode="after")
    def price_matches_access_type(self) -> "StreamCreate":
        if self.access_type == AccessType.PAID and self.price <= 0:
            raise ValueError("paid streams must have a positive price")
        if self.access_type != AccessType.PAID and self.price != 0:
            raise ValueError("only paid streams may have a price")
        return self


class StreamActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: str = Field(min_length=6, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("room_id")
    @classmethod
    def normalize_room_id(cls, value: str) -> str:
        return value.strip()


class StreamResponse(BaseModel):
    id: UUID
    creator_id: UUID
    title: str
    description: str
    objective: str
    starts_at: datetime
    estimated_duration_minutes: int
    category_id: UUID
    level: Level
    price: Decimal
    access_type: AccessType
    created_at: datetime
    live_started_at: datetime | None = None
    live_ended_at: datetime | None = None
    live_room_id: str | None = None


class ReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minutes_before: int = Field(default=30, ge=0, le=10080)


class ReminderResponse(BaseModel):
    stream_id: UUID
    notify_at: datetime


class NotificationResponse(BaseModel):
    id: UUID
    kind: NotificationKind
    title: str
    body: str
    data: dict[str, str]
    created_at: datetime
    read_at: datetime | None
