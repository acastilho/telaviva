from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Category:
    id: UUID
    slug: str
    name: str


@dataclass(frozen=True)
class CreatorProfile:
    user_id: UUID
    photo_url: str | None
    name: str
    bio: str
    profession: str
    specialties: list[str]
    tools: list[str]
    languages: list[str]
    categories: list[Category]
    social_links: dict[str, str]
    is_verified: bool
    default_price: Decimal | None
    accepts_tips: bool
