from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class InteractionKind(StrEnum):
    MESSAGE = "message"
    QUESTION = "question"
    REACTION = "reaction"


class ModerationAction(StrEnum):
    MUTE = "mute"
    BAN = "ban"


@dataclass(frozen=True)
class InteractionSettings:
    stream_id: UUID
    chat_enabled: bool = True
    questions_enabled: bool = True
    reactions_enabled: bool = True


@dataclass(frozen=True)
class InteractionEvent:
    id: UUID
    stream_id: UUID
    user_id: UUID
    kind: InteractionKind
    content: str
    created_at: datetime


@dataclass(frozen=True)
class Report:
    id: UUID
    stream_id: UUID
    reporter_id: UUID
    event_id: UUID
    reason: str
    created_at: datetime
