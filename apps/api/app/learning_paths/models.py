from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PathLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    ALL_LEVELS = "ALL_LEVELS"


@dataclass(frozen=True)
class PathLesson:
    id: UUID
    module_id: UUID
    recording_id: UUID
    title: str
    description: str
    position: int
    completed: bool = False


@dataclass(frozen=True)
class PathModule:
    id: UUID
    path_id: UUID
    title: str
    description: str
    position: int
    lessons: tuple[PathLesson, ...] = ()


@dataclass(frozen=True)
class LearningPath:
    id: UUID
    creator_id: UUID
    title: str
    description: str
    level: PathLevel
    price: Decimal | None
    published: bool
    created_at: datetime
    updated_at: datetime
    modules: tuple[PathModule, ...] = ()
    progress_percent: int = 0
