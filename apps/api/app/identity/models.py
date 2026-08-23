from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "ADMIN"
    CREATOR = "CREATOR"
    VIEWER = "VIEWER"


class Audience(StrEnum):
    CHILD = "CHILD"
    TEEN = "TEEN"
    ADULT = "ADULT"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    role: Role
    created_at: datetime
    audience: Audience = Audience.ADULT
    guardian_email: str | None = None
