from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.learning_paths.models import LearningPath, PathLesson, PathLevel, PathModule


class PathNotFoundError(Exception):
    pass


class InvalidPathStructureError(Exception):
    pass


class LearningPathRepository(Protocol):
    async def create(self, creator_id: UUID, **values: object) -> LearningPath: ...
    async def get(self, path_id: UUID, user_id: UUID | None = None) -> LearningPath | None: ...
    async def list_published(self, user_id: UUID | None = None) -> list[LearningPath]: ...
    async def add_module(self, path_id: UUID, creator_id: UUID, **values: object) -> LearningPath: ...
    async def add_lesson(self, module_id: UUID, creator_id: UUID, **values: object) -> LearningPath: ...
    async def reorder_modules(self, path_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath: ...
    async def reorder_lessons(self, module_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath: ...
    async def publish(self, path_id: UUID, creator_id: UUID) -> LearningPath: ...
    async def set_progress(self, lesson_id: UUID, user_id: UUID, completed: bool) -> LearningPath: ...


class PostgresLearningPathRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def _load(self, connection: asyncpg.Connection, path_id: UUID, user_id: UUID | None = None) -> LearningPath | None:
        row = await connection.fetchrow("SELECT * FROM learning_paths WHERE id=$1", path_id)
        if row is None:
            return None
        module_rows = await connection.fetch("SELECT * FROM learning_path_modules WHERE path_id=$1 ORDER BY position,id", path_id)
        modules: list[PathModule] = []
        completed = total = 0
        for module in module_rows:
            lesson_rows = await connection.fetch(
                "SELECT l.*,COALESCE(p.completed,false) completed FROM learning_path_lessons l LEFT JOIN learning_path_progress p ON p.lesson_id=l.id AND p.user_id=$2 WHERE l.module_id=$1 ORDER BY l.position,l.id",
                module["id"], user_id,
            )
            lessons = tuple(PathLesson(
                item["id"], item["module_id"], item["recording_id"], item["title"],
                item["description"], item["position"], item["completed"],
            ) for item in lesson_rows)
            total += len(lessons)
            completed += sum(lesson.completed for lesson in lessons)
            modules.append(PathModule(module["id"], path_id, module["title"], module["description"], module["position"], lessons))
        return LearningPath(
            row["id"], row["creator_id"], row["title"], row["description"],
            PathLevel(row["level"]), row["price"], row["published"], row["created_at"],
            row["updated_at"], tuple(modules), round(completed * 100 / total) if total else 0,
        )

    async def create(self, creator_id: UUID, **values: object) -> LearningPath:
        connection = await self._connect()
        try:
            path_id = uuid4()
            await connection.execute(
                "INSERT INTO learning_paths (id,creator_id,title,description,level,price) VALUES ($1,$2,$3,$4,$5,$6)",
                path_id, creator_id, values["title"], values["description"], str(values["level"]), values["price"],
            )
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def get(self, path_id: UUID, user_id: UUID | None = None) -> LearningPath | None:
        connection = await self._connect()
        try:
            return await self._load(connection, path_id, user_id)
        finally:
            await connection.close()

    async def list_published(self, user_id: UUID | None = None) -> list[LearningPath]:
        connection = await self._connect()
        try:
            ids = await connection.fetch("SELECT id FROM learning_paths WHERE published ORDER BY created_at DESC,id")
            return [path for row in ids if (path := await self._load(connection, row["id"], user_id))]
        finally:
            await connection.close()

    async def _owned_path(self, connection: asyncpg.Connection, path_id: UUID, creator_id: UUID) -> None:
        if not await connection.fetchval("SELECT EXISTS(SELECT 1 FROM learning_paths WHERE id=$1 AND creator_id=$2)", path_id, creator_id):
            raise PathNotFoundError

    async def add_module(self, path_id: UUID, creator_id: UUID, **values: object) -> LearningPath:
        connection = await self._connect()
        try:
            await self._owned_path(connection, path_id, creator_id)
            await connection.execute("INSERT INTO learning_path_modules (id,path_id,title,description,position) VALUES ($1,$2,$3,$4,$5)", uuid4(), path_id, values["title"], values["description"], values["position"])
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def add_lesson(self, module_id: UUID, creator_id: UUID, **values: object) -> LearningPath:
        connection = await self._connect()
        try:
            path_id = await connection.fetchval("SELECT p.id FROM learning_paths p JOIN learning_path_modules m ON m.path_id=p.id WHERE m.id=$1 AND p.creator_id=$2", module_id, creator_id)
            if path_id is None:
                raise PathNotFoundError
            try:
                await connection.execute("INSERT INTO learning_path_lessons (id,module_id,recording_id,title,description,position) VALUES ($1,$2,$3,$4,$5,$6)", uuid4(), module_id, values["recording_id"], values["title"], values["description"], values["position"])
            except asyncpg.ForeignKeyViolationError as error:
                raise InvalidPathStructureError from error
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def _reorder(self, connection: asyncpg.Connection, table: str, parent: str, parent_id: UUID, ids: list[UUID]) -> None:
        actual = await connection.fetch(f"SELECT id FROM {table} WHERE {parent}=$1", parent_id)
        if set(ids) != {row["id"] for row in actual} or len(ids) != len(set(ids)):
            raise InvalidPathStructureError
        await connection.execute(f"UPDATE {table} SET position=position+1000000 WHERE {parent}=$1", parent_id)
        await connection.executemany(f"UPDATE {table} SET position=$1 WHERE id=$2", list(enumerate(ids)))

    async def reorder_modules(self, path_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath:
        connection = await self._connect()
        try:
            await self._owned_path(connection, path_id, creator_id)
            await self._reorder(connection, "learning_path_modules", "path_id", path_id, ids)
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def reorder_lessons(self, module_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath:
        connection = await self._connect()
        try:
            path_id = await connection.fetchval("SELECT p.id FROM learning_paths p JOIN learning_path_modules m ON m.path_id=p.id WHERE m.id=$1 AND p.creator_id=$2", module_id, creator_id)
            if path_id is None:
                raise PathNotFoundError
            await self._reorder(connection, "learning_path_lessons", "module_id", module_id, ids)
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def publish(self, path_id: UUID, creator_id: UUID) -> LearningPath:
        connection = await self._connect()
        try:
            await self._owned_path(connection, path_id, creator_id)
            count = await connection.fetchval("SELECT count(*) FROM learning_path_lessons l JOIN learning_path_modules m ON m.id=l.module_id WHERE m.path_id=$1", path_id)
            if not count:
                raise InvalidPathStructureError
            await connection.execute("UPDATE learning_paths SET published=true,updated_at=now() WHERE id=$1", path_id)
            result = await self._load(connection, path_id)
            assert result is not None
            return result
        finally:
            await connection.close()

    async def set_progress(self, lesson_id: UUID, user_id: UUID, completed: bool) -> LearningPath:
        connection = await self._connect()
        try:
            path_id = await connection.fetchval("SELECT p.id FROM learning_paths p JOIN learning_path_modules m ON m.path_id=p.id JOIN learning_path_lessons l ON l.module_id=m.id WHERE l.id=$1 AND p.published", lesson_id)
            if path_id is None:
                raise PathNotFoundError
            await connection.execute("INSERT INTO learning_path_progress (lesson_id,user_id,completed) VALUES ($1,$2,$3) ON CONFLICT (lesson_id,user_id) DO UPDATE SET completed=$3,updated_at=now()", lesson_id, user_id, completed)
            result = await self._load(connection, path_id, user_id)
            assert result is not None
            return result
        finally:
            await connection.close()
