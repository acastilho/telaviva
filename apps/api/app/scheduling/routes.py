from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.routes import get_current_user, require_roles
from app.scheduling.models import Notification, ScheduledStream
from app.scheduling.repository import (
    InvalidReminderTimeError,
    PostgresSchedulingRepository,
    SchedulingRepository,
    StreamNotFoundError,
    UnknownCategoryError,
)
from app.scheduling.schemas import (
    NotificationResponse,
    ReminderCreate,
    ReminderResponse,
    StreamActivationRequest,
    StreamCreate,
    StreamResponse,
)

router = APIRouter(tags=["schedule"])


def get_scheduling_repository(settings: Settings = Depends(get_settings)) -> SchedulingRepository:
    return PostgresSchedulingRepository(settings)


def _stream_response(stream: ScheduledStream) -> StreamResponse:
    return StreamResponse.model_validate(stream, from_attributes=True)


def _notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse.model_validate(notification, from_attributes=True)


@router.post("/streams", response_model=StreamResponse, status_code=status.HTTP_201_CREATED)
async def create_stream(
    body: StreamCreate,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> StreamResponse:
    try:
        stream = await repository.create_stream(creator.id, **body.model_dump())
    except UnknownCategoryError as error:
        raise HTTPException(status_code=422, detail="Category does not exist") from error
    return _stream_response(stream)


@router.get("/streams/active", response_model=list[StreamResponse])
async def list_active_streams(
    repository: SchedulingRepository = Depends(get_scheduling_repository),
) -> list[StreamResponse]:
    """Return only transmissions explicitly started by their creator and not ended."""
    return [_stream_response(item) for item in await repository.list_active_streams()]


@router.post("/streams/{stream_id}/activate", response_model=StreamResponse)
async def activate_stream(
    stream_id: UUID,
    body: StreamActivationRequest,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> StreamResponse:
    try:
        stream = await repository.activate_stream(stream_id, creator.id, body.room_id, datetime.now(UTC))
    except StreamNotFoundError as error:
        raise HTTPException(status_code=404, detail="Stream not found") from error
    return _stream_response(stream)


@router.post("/streams/{stream_id}/finish", response_model=StreamResponse)
async def finish_stream(
    stream_id: UUID,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> StreamResponse:
    try:
        stream = await repository.finish_stream(stream_id, creator.id, datetime.now(UTC))
    except StreamNotFoundError as error:
        raise HTTPException(status_code=404, detail="Active stream not found") from error
    return _stream_response(stream)


@router.get("/streams", response_model=list[StreamResponse])
async def list_streams(
    creator_id: UUID | None = None,
    starts_after: datetime = Query(default_factory=lambda: datetime.now(UTC)),
    repository: SchedulingRepository = Depends(get_scheduling_repository),
) -> list[StreamResponse]:
    if starts_after.tzinfo is None or starts_after.utcoffset() is None:
        raise HTTPException(status_code=422, detail="starts_after timezone is required")
    return [_stream_response(item) for item in await repository.list_streams(creator_id=creator_id, starts_after=starts_after)]


@router.put("/creators/{creator_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_creator(
    creator_id: UUID,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> None:
    if user.id == creator_id:
        raise HTTPException(status_code=422, detail="Creators cannot follow themselves")
    try:
        await repository.follow(user.id, creator_id)
    except StreamNotFoundError as error:
        raise HTTPException(status_code=404, detail="Creator not found") from error


@router.delete("/creators/{creator_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_creator(
    creator_id: UUID,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> None:
    await repository.unfollow(user.id, creator_id)


@router.get("/agenda/me", response_model=list[StreamResponse])
async def my_agenda(
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> list[StreamResponse]:
    return [_stream_response(item) for item in await repository.list_agenda(user.id, datetime.now(UTC))]


@router.put("/streams/{stream_id}/reminder", response_model=ReminderResponse)
async def set_reminder(
    stream_id: UUID,
    body: ReminderCreate,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> ReminderResponse:
    try:
        notify_at = await repository.add_reminder(user.id, stream_id, body.minutes_before)
    except StreamNotFoundError as error:
        raise HTTPException(status_code=404, detail="Stream not found") from error
    except InvalidReminderTimeError as error:
        raise HTTPException(status_code=422, detail="Reminder time must be in the future") from error
    return ReminderResponse(stream_id=stream_id, notify_at=notify_at)


@router.delete("/streams/{stream_id}/reminder", status_code=status.HTTP_204_NO_CONTENT)
async def remove_reminder(
    stream_id: UUID,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> None:
    await repository.remove_reminder(user.id, stream_id)


@router.get("/notifications", response_model=list[NotificationResponse])
async def notifications(
    unread_only: bool = False,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    return [_notification_response(item) for item in await repository.list_notifications(user.id, unread_only)]


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: UUID,
    repository: SchedulingRepository = Depends(get_scheduling_repository),
    user: User = Depends(get_current_user),
) -> None:
    if not await repository.mark_notification_read(user.id, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
