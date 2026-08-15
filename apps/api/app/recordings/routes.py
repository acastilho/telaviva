from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.commerce.repository import CommerceRepository, ProductNotFoundError
from app.commerce.routes import get_commerce_repository
from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.routes import get_current_user, require_roles
from app.recordings.models import Recording
from app.recordings.processor import DeferredRecordingProcessor, RecordingProcessor
from app.recordings.repository import (
    InvalidRecordingTransitionError,
    PostgresRecordingRepository,
    RecordingRepository,
    StreamNotFoundError,
)
from app.recordings.schemas import ProcessingComplete, ProcessingFailed, RecordingResponse
from app.recordings.service import RecordingService
from app.recordings.storage import RecordingStorage, S3RecordingStorage

router = APIRouter(tags=["recordings"])


def get_recording_repository(
    settings: Settings = Depends(get_settings),
) -> RecordingRepository:
    return PostgresRecordingRepository(settings)


def get_recording_storage(settings: Settings = Depends(get_settings)) -> RecordingStorage:
    return S3RecordingStorage(settings)


def get_recording_processor() -> RecordingProcessor:
    return DeferredRecordingProcessor()


def get_recording_service(
    repository: RecordingRepository = Depends(get_recording_repository),
    storage: RecordingStorage = Depends(get_recording_storage),
    processor: RecordingProcessor = Depends(get_recording_processor),
    settings: Settings = Depends(get_settings),
) -> RecordingService:
    return RecordingService(repository, storage, processor, settings)


async def _owner_or_admin(
    stream_id: UUID, user: User, repository: RecordingRepository
) -> None:
    creator_id = await repository.stream_creator(stream_id)
    if creator_id is None:
        raise HTTPException(404, "Stream not found")
    if creator_id != user.id and user.role is not Role.ADMIN:
        raise HTTPException(403, "Only the creator or an admin can control the broadcast")


def _response(
    recording: Recording,
    storage: RecordingStorage | None = None,
    ttl: int = 900,
) -> RecordingResponse:
    response = RecordingResponse.model_validate(recording)
    if storage and recording.playback_key and recording.thumbnail_key:
        response.playback_url = storage.download_url(recording.playback_key, ttl)
        response.thumbnail_url = storage.download_url(recording.thumbnail_key, ttl)
    return response


@router.post("/streams/{stream_id}/broadcast/start", response_model=RecordingResponse)
async def start_broadcast(
    stream_id: UUID,
    repository: RecordingRepository = Depends(get_recording_repository),
    service: RecordingService = Depends(get_recording_service),
    user: User = Depends(get_current_user),
) -> RecordingResponse:
    """Start the broadcast and its recording in the same lifecycle operation."""
    await _owner_or_admin(stream_id, user, repository)
    try:
        return _response(await service.broadcast_started(stream_id))
    except StreamNotFoundError as error:
        raise HTTPException(404, "Stream not found") from error


@router.post("/streams/{stream_id}/broadcast/end", response_model=RecordingResponse)
async def end_broadcast(
    stream_id: UUID,
    repository: RecordingRepository = Depends(get_recording_repository),
    service: RecordingService = Depends(get_recording_service),
    user: User = Depends(get_current_user),
) -> RecordingResponse:
    """End the broadcast and enqueue recording processing atomically from the caller view."""
    await _owner_or_admin(stream_id, user, repository)
    try:
        return _response(await service.broadcast_ended(stream_id))
    except InvalidRecordingTransitionError as error:
        raise HTTPException(409, "Recording is not active") from error


@router.put("/recordings/{recording_id}/complete", response_model=RecordingResponse)
async def complete_processing(
    recording_id: UUID,
    body: ProcessingComplete,
    repository: RecordingRepository = Depends(get_recording_repository),
    _: User = require_roles(Role.ADMIN),  # type: ignore[assignment]
) -> RecordingResponse:
    """Receive the normalized completion event from a trusted media worker adapter."""
    try:
        return _response(await repository.complete(recording_id, **body.model_dump()))
    except InvalidRecordingTransitionError as error:
        raise HTTPException(409, "Recording is not processing") from error


@router.put("/recordings/{recording_id}/failed", response_model=RecordingResponse)
async def fail_processing(
    recording_id: UUID,
    body: ProcessingFailed,
    repository: RecordingRepository = Depends(get_recording_repository),
    _: User = require_roles(Role.ADMIN),  # type: ignore[assignment]
) -> RecordingResponse:
    try:
        return _response(await repository.fail(recording_id, body.reason.strip()))
    except InvalidRecordingTransitionError as error:
        raise HTTPException(409, "Recording cannot transition to failed") from error


@router.get("/streams/{stream_id}/recording", response_model=RecordingResponse)
async def get_recording(
    stream_id: UUID,
    repository: RecordingRepository = Depends(get_recording_repository),
    commerce: CommerceRepository = Depends(get_commerce_repository),
    storage: RecordingStorage = Depends(get_recording_storage),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RecordingResponse:
    recording = await repository.get_for_stream(stream_id)
    if recording is None:
        raise HTTPException(404, "Recording not found")
    try:
        access = await commerce.check_access(stream_id, user.id)
    except ProductNotFoundError as error:
        raise HTTPException(404, "Stream not found") from error
    if not access.granted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Entitlement or invitation required")
    return _response(recording, storage, settings.recording_url_ttl_seconds)
