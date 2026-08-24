from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class Level(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    ALL_LEVELS = "ALL_LEVELS"


class AccessType(StrEnum):
    FREE = "FREE"
    PAID = "PAID"
    SUBSCRIBERS = "SUBSCRIBERS"
    PRIVATE = "PRIVATE"


class NotificationKind(StrEnum):
    STREAM_SCHEDULED = "STREAM_SCHEDULED"
    STREAM_REMINDER = "STREAM_REMINDER"


@dataclass(frozen=True)
class ScheduledStream:
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


@dataclass(frozen=True)
class Notification:
    id: UUID
    user_id: UUID
    kind: NotificationKind
    title: str
    body: str
    data: dict[str, str]
    created_at: datetime
    read_at: datetime | None
