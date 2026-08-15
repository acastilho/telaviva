from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class CategoryResponse(BaseModel):
    id: UUID
    slug: str
    name: str


class CreatorProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_url: HttpUrl | None = None
    name: str = Field(min_length=1, max_length=120)
    bio: str = Field(default="", max_length=2000)
    profession: str = Field(min_length=1, max_length=120)
    specialties: list[str] = Field(default_factory=list, max_length=20)
    tools: list[str] = Field(default_factory=list, max_length=30)
    languages: list[str] = Field(default_factory=list, max_length=20)
    category_ids: list[UUID] = Field(default_factory=list, max_length=16)
    social_links: dict[str, HttpUrl] = Field(default_factory=dict, max_length=20)
    default_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    accepts_tips: bool = False

    @field_validator("name", "profession")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("specialties", "tools", "languages")
    @classmethod
    def normalize_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("items must not be blank")
        if len(set(item.casefold() for item in normalized)) != len(normalized):
            raise ValueError("items must be unique")
        return normalized

    @field_validator("category_ids")
    @classmethod
    def unique_categories(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError("categories must be unique")
        return values


class CreatorProfileResponse(BaseModel):
    user_id: UUID
    photo_url: str | None
    name: str
    bio: str
    profession: str
    specialties: list[str]
    tools: list[str]
    languages: list[str]
    categories: list[CategoryResponse]
    social_links: dict[str, str]
    is_verified: bool
    default_price: Decimal | None
    accepts_tips: bool
