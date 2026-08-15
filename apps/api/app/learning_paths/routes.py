from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.routes import get_current_user, require_roles
from app.learning_paths.models import LearningPath
from app.learning_paths.repository import (
    InvalidPathStructureError,
    LearningPathRepository,
    PathNotFoundError,
    PostgresLearningPathRepository,
)
from app.learning_paths.schemas import (
    LessonCreate,
    LessonProgressUpdate,
    ModuleCreate,
    PathCreate,
    PathResponse,
    ReorderRequest,
)

router = APIRouter(prefix="/learning-paths", tags=["learning paths"])


def get_learning_path_repository(settings: Settings = Depends(get_settings)) -> LearningPathRepository:
    return PostgresLearningPathRepository(settings)


def _response(path: LearningPath) -> PathResponse:
    return PathResponse.model_validate(path)


def _not_found(error: PathNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail="Learning path not found")


@router.post("", response_model=PathResponse, status_code=status.HTTP_201_CREATED)
async def create_path(
    body: PathCreate,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    return _response(await repository.create(creator.id, **body.model_dump()))


@router.get("", response_model=list[PathResponse])
async def list_paths(
    repository: LearningPathRepository = Depends(get_learning_path_repository),
) -> list[PathResponse]:
    return [_response(path) for path in await repository.list_published()]


@router.get("/{path_id}", response_model=PathResponse)
async def get_path(
    path_id: UUID,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    user: User = Depends(get_current_user),
) -> PathResponse:
    path = await repository.get(path_id, user.id)
    if path is None or (not path.published and path.creator_id != user.id and user.role is not Role.ADMIN):
        raise HTTPException(404, "Learning path not found")
    return _response(path)


@router.post("/{path_id}/modules", response_model=PathResponse, status_code=201)
async def add_module(
    path_id: UUID,
    body: ModuleCreate,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    try:
        return _response(await repository.add_module(path_id, creator.id, **body.model_dump()))
    except PathNotFoundError as error:
        raise _not_found(error) from error


@router.post("/modules/{module_id}/lessons", response_model=PathResponse, status_code=201)
async def add_lesson(
    module_id: UUID,
    body: LessonCreate,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    try:
        return _response(await repository.add_lesson(module_id, creator.id, **body.model_dump()))
    except PathNotFoundError as error:
        raise _not_found(error) from error
    except InvalidPathStructureError as error:
        raise HTTPException(422, "Recording does not exist") from error


@router.put("/{path_id}/modules/order", response_model=PathResponse)
async def reorder_modules(
    path_id: UUID,
    body: ReorderRequest,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    try:
        return _response(await repository.reorder_modules(path_id, creator.id, body.ordered_ids))
    except PathNotFoundError as error:
        raise _not_found(error) from error
    except InvalidPathStructureError as error:
        raise HTTPException(422, "Order must contain every module exactly once") from error


@router.put("/modules/{module_id}/lessons/order", response_model=PathResponse)
async def reorder_lessons(
    module_id: UUID,
    body: ReorderRequest,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    try:
        return _response(await repository.reorder_lessons(module_id, creator.id, body.ordered_ids))
    except PathNotFoundError as error:
        raise _not_found(error) from error
    except InvalidPathStructureError as error:
        raise HTTPException(422, "Order must contain every lesson exactly once") from error


@router.put("/{path_id}/publish", response_model=PathResponse)
async def publish_path(
    path_id: UUID,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> PathResponse:
    try:
        return _response(await repository.publish(path_id, creator.id))
    except PathNotFoundError as error:
        raise _not_found(error) from error
    except InvalidPathStructureError as error:
        raise HTTPException(409, "A path needs at least one lesson before publication") from error


@router.put("/lessons/{lesson_id}/progress", response_model=PathResponse)
async def update_lesson_progress(
    lesson_id: UUID,
    body: LessonProgressUpdate,
    repository: LearningPathRepository = Depends(get_learning_path_repository),
    user: User = Depends(get_current_user),
) -> PathResponse:
    try:
        return _response(await repository.set_progress(lesson_id, user.id, body.completed))
    except PathNotFoundError as error:
        raise _not_found(error) from error
