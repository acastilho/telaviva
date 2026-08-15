from uuid import UUID, uuid4

from app.config import Settings
from app.recordings.models import Recording
from app.recordings.processor import RecordingProcessor
from app.recordings.repository import RecordingRepository
from app.recordings.storage import RecordingStorage


class RecordingService:
    def __init__(
        self,
        repository: RecordingRepository,
        storage: RecordingStorage,
        processor: RecordingProcessor,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._processor = processor
        self._url_ttl = settings.recording_url_ttl_seconds

    async def broadcast_started(self, stream_id: UUID) -> Recording:
        existing = await self._repository.get_for_stream(stream_id)
        if existing is not None:
            return existing
        source_key = f"streams/{stream_id}/source/{uuid4()}.webm"
        recording = await self._repository.start(stream_id, source_key)
        upload_url = self._storage.upload_url(source_key, "video/webm", self._url_ttl)
        await self._processor.start(recording, upload_url)
        return recording

    async def broadcast_ended(self, stream_id: UUID) -> Recording:
        recording = await self._repository.stop(stream_id)
        await self._processor.finish(recording)
        return recording
