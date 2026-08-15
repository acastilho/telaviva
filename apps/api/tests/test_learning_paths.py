from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.learning_paths.models import LearningPath, PathLesson, PathModule
from app.learning_paths.repository import InvalidPathStructureError, PathNotFoundError
from app.learning_paths.routes import get_learning_path_repository
from app.main import app

creator = User(uuid4(), "creator@paths.test", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "viewer@paths.test", "hash", Role.VIEWER, datetime.now(UTC))
current_user = creator


class MemoryPaths:
    def __init__(self) -> None:
        self.paths: dict[UUID, LearningPath] = {}

    async def create(self, creator_id: UUID, **values: object) -> LearningPath:
        now = datetime.now(UTC)
        path = LearningPath(uuid4(), creator_id, values["title"], values["description"], values["level"], values["price"], False, now, now)  # type: ignore[arg-type]
        self.paths[path.id] = path
        return path

    async def get(self, path_id: UUID, user_id: UUID | None = None) -> LearningPath | None:
        path = self.paths.get(path_id)
        if path is None:
            return None
        done = sum(lesson.completed for module in path.modules for lesson in module.lessons)
        total = sum(len(module.lessons) for module in path.modules)
        return replace(path, progress_percent=round(done * 100 / total) if total else 0)

    async def list_published(self, user_id: UUID | None = None) -> list[LearningPath]:
        return [path for path in self.paths.values() if path.published]

    def owned(self, path_id: UUID, owner: UUID) -> LearningPath:
        path = self.paths.get(path_id)
        if path is None or path.creator_id != owner:
            raise PathNotFoundError
        return path

    async def add_module(self, path_id: UUID, creator_id: UUID, **values: object) -> LearningPath:
        path = self.owned(path_id, creator_id)
        module = PathModule(uuid4(), path_id, values["title"], values["description"], values["position"])  # type: ignore[arg-type]
        self.paths[path_id] = replace(path, modules=path.modules + (module,))
        return self.paths[path_id]

    async def add_lesson(self, module_id: UUID, creator_id: UUID, **values: object) -> LearningPath:
        for path in self.paths.values():
            if path.creator_id == creator_id and any(module.id == module_id for module in path.modules):
                lesson = PathLesson(uuid4(), module_id, values["recording_id"], values["title"], values["description"], values["position"])  # type: ignore[arg-type]
                modules = tuple(replace(module, lessons=module.lessons + (lesson,)) if module.id == module_id else module for module in path.modules)
                self.paths[path.id] = replace(path, modules=modules)
                return self.paths[path.id]
        raise PathNotFoundError

    async def reorder_modules(self, path_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath:
        path = self.owned(path_id, creator_id)
        if set(ids) != {module.id for module in path.modules} or len(ids) != len(set(ids)):
            raise InvalidPathStructureError
        by_id = {module.id: module for module in path.modules}
        self.paths[path_id] = replace(path, modules=tuple(replace(by_id[item], position=index) for index, item in enumerate(ids)))
        return self.paths[path_id]

    async def reorder_lessons(self, module_id: UUID, creator_id: UUID, ids: list[UUID]) -> LearningPath:
        raise NotImplementedError

    async def publish(self, path_id: UUID, creator_id: UUID) -> LearningPath:
        path = self.owned(path_id, creator_id)
        if not any(module.lessons for module in path.modules):
            raise InvalidPathStructureError
        self.paths[path_id] = replace(path, published=True)
        return self.paths[path_id]

    async def set_progress(self, lesson_id: UUID, user_id: UUID, completed: bool) -> LearningPath:
        for path in self.paths.values():
            if path.published and any(lesson.id == lesson_id for module in path.modules for lesson in module.lessons):
                modules = tuple(replace(module, lessons=tuple(replace(lesson, completed=completed) if lesson.id == lesson_id else lesson for lesson in module.lessons)) for module in path.modules)
                self.paths[path.id] = replace(path, modules=modules)
                result = await self.get(path.id, user_id)
                assert result is not None
                return result
        raise PathNotFoundError


repository = MemoryPaths()
app.dependency_overrides[get_learning_path_repository] = lambda: repository
app.dependency_overrides[get_current_user] = lambda: current_user
client = TestClient(app)


def setup_function() -> None:
    global current_user
    current_user = creator
    repository.paths.clear()


def create_path() -> dict[str, object]:
    response = client.post("/learning-paths", json={"title": "Design completo", "description": "Do fundamento ao portfólio", "level": "BEGINNER", "price": "49.90"})
    assert response.status_code == 201
    return response.json()


def test_creator_builds_orders_and_publishes_path() -> None:
    path = create_path()
    first = client.post(f"/learning-paths/{path['id']}/modules", json={"title": "Prática", "position": 1}).json()
    second = client.post(f"/learning-paths/{path['id']}/modules", json={"title": "Fundamentos", "position": 0}).json()
    ids = [module["id"] for module in second["modules"]]
    ordered = client.put(f"/learning-paths/{path['id']}/modules/order", json={"ordered_ids": list(reversed(ids))})
    assert [module["position"] for module in ordered.json()["modules"]] == [0, 1]
    module_id = first["modules"][0]["id"]
    lesson = client.post(f"/learning-paths/modules/{module_id}/lessons", json={"recording_id": str(uuid4()), "title": "Aula 1", "position": 0})
    assert lesson.status_code == 201
    assert client.put(f"/learning-paths/{path['id']}/publish").json()["published"] is True
    assert len(client.get("/learning-paths").json()) == 1


def test_draft_permissions_and_publication_validation() -> None:
    path = create_path()
    global current_user
    current_user = viewer
    assert client.get(f"/learning-paths/{path['id']}").status_code == 404
    assert client.post("/learning-paths", json={"title": "X", "level": "BEGINNER"}).status_code == 403
    current_user = creator
    assert client.put(f"/learning-paths/{path['id']}/publish").status_code == 409


def test_progress_is_aggregated_and_payload_is_validated() -> None:
    path = create_path()
    built = client.post(f"/learning-paths/{path['id']}/modules", json={"title": "Módulo", "position": 0}).json()
    module_id = built["modules"][0]["id"]
    lesson_ids = []
    for position in range(2):
        response = client.post(f"/learning-paths/modules/{module_id}/lessons", json={"recording_id": str(uuid4()), "title": f"Aula {position + 1}", "position": position})
        lesson_ids = [lesson["id"] for lesson in response.json()["modules"][0]["lessons"]]
    client.put(f"/learning-paths/{path['id']}/publish")
    global current_user
    current_user = viewer
    progress = client.put(f"/learning-paths/lessons/{lesson_ids[0]}/progress", json={"completed": True})
    assert progress.json()["progress_percent"] == 50
    current_user = creator
    assert client.post("/learning-paths", json={"title": " ", "level": "BEGINNER"}).status_code == 422
    assert client.post("/learning-paths", json={"title": "X", "level": "BEGINNER", "price": -1}).status_code == 422
