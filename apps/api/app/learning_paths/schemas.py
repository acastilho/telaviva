from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.learning_paths.models import PathLevel


class PathCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    level: PathLevel
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @field_validator("title")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("must not be blank")
        return value


class ModuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    position: int = Field(ge=0)

    @field_validator("title")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("must not be blank")
        return value


class LessonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recording_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    position: int = Field(ge=0)


class ReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ordered_ids: list[UUID] = Field(min_length=1)


class LessonProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool = True


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recording_id: UUID
    title: str
    description: str
    position: int
    completed: bool


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    position: int
    lessons: tuple[LessonResponse, ...]


class PathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    creator_id: UUID
    title: str
    description: str
    level: PathLevel
    price: Decimal | None
    published: bool
    progress_percent: int
    modules: tuple[ModuleResponse, ...]
