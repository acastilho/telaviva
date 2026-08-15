import json
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import asyncpg

from app.config import Settings
from app.creators.models import Category, CreatorProfile


class UnknownCategoryError(Exception):
    pass


class CreatorRepository(Protocol):
    async def list_categories(self) -> list[Category]: ...
    async def get_profile(self, user_id: UUID) -> CreatorProfile | None: ...
    async def upsert_profile(
        self,
        user_id: UUID,
        *,
        photo_url: str | None,
        name: str,
        bio: str,
        profession: str,
        specialties: list[str],
        tools: list[str],
        languages: list[str],
        category_ids: list[UUID],
        social_links: dict[str, str],
        default_price: Decimal | None,
        accepts_tips: bool,
    ) -> CreatorProfile: ...


def _category(record: asyncpg.Record) -> Category:
    return Category(id=record["id"], slug=record["slug"], name=record["name"])


class PostgresCreatorRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def list_categories(self) -> list[Category]:
        connection = await self._connect()
        try:
            records = await connection.fetch("SELECT id,slug,name FROM categories ORDER BY name")
            return [_category(record) for record in records]
        finally:
            await connection.close()

    async def get_profile(self, user_id: UUID) -> CreatorProfile | None:
        connection = await self._connect()
        try:
            return await self._get_profile(connection, user_id)
        finally:
            await connection.close()

    async def _get_profile(
        self, connection: asyncpg.Connection, user_id: UUID
    ) -> CreatorProfile | None:
        record = await connection.fetchrow(
            "SELECT * FROM creator_profiles WHERE user_id=$1", user_id
        )
        if record is None:
            return None
        category_records = await connection.fetch(
            "SELECT c.id,c.slug,c.name FROM categories c "
            "JOIN creator_categories cc ON cc.category_id=c.id "
            "WHERE cc.creator_id=$1 ORDER BY c.name",
            user_id,
        )
        return CreatorProfile(
            user_id=record["user_id"], photo_url=record["photo_url"], name=record["name"],
            bio=record["bio"], profession=record["profession"],
            specialties=list(record["specialties"]), tools=list(record["tools"]),
            languages=list(record["languages"]),
            categories=[_category(category) for category in category_records],
            social_links=json.loads(record["social_links"]), is_verified=record["is_verified"],
            default_price=record["default_price"], accepts_tips=record["accepts_tips"],
        )

    async def upsert_profile(
        self, user_id: UUID, *, photo_url: str | None, name: str, bio: str,
        profession: str, specialties: list[str], tools: list[str], languages: list[str],
        category_ids: list[UUID], social_links: dict[str, str], default_price: Decimal | None,
        accepts_tips: bool,
    ) -> CreatorProfile:
        connection = await self._connect()
        try:
            async with connection.transaction():
                count = await connection.fetchval(
                    "SELECT count(*) FROM categories WHERE id=ANY($1::uuid[])", category_ids
                )
                if count != len(category_ids):
                    raise UnknownCategoryError
                await connection.execute(
                    "INSERT INTO creator_profiles "
                    "(user_id,photo_url,name,bio,profession,specialties,tools,languages,"
                    "social_links,"
                    "default_price,accepts_tips) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) "
                    "ON CONFLICT (user_id) DO UPDATE SET photo_url=EXCLUDED.photo_url,"
                    "name=EXCLUDED.name,bio=EXCLUDED.bio,profession=EXCLUDED.profession,"
                    "specialties=EXCLUDED.specialties,tools=EXCLUDED.tools,"
                    "languages=EXCLUDED.languages,"
                    "social_links=EXCLUDED.social_links,default_price=EXCLUDED.default_price,"
                    "accepts_tips=EXCLUDED.accepts_tips,updated_at=now()",
                    user_id, photo_url, name, bio, profession, specialties, tools, languages,
                    json.dumps(social_links), default_price, accepts_tips,
                )
                await connection.execute(
                    "DELETE FROM creator_categories WHERE creator_id=$1", user_id
                )
                if category_ids:
                    await connection.executemany(
                        "INSERT INTO creator_categories (creator_id,category_id) VALUES ($1,$2)",
                        [(user_id, category_id) for category_id in category_ids],
                    )
                profile = await self._get_profile(connection, user_id)
                assert profile is not None
                return profile
        finally:
            await connection.close()
