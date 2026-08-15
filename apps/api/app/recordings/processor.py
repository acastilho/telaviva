from typing import Protocol

from app.recordings.models import Recording


class RecordingProcessor(Protocol):
    """Boundary for the media worker/provider that captures and transcodes a live stream."""

    async def start(self, recording: Recording, upload_url: str) -> None: ...
    async def finish(self, recording: Recording) -> None: ...


class DeferredRecordingProcessor:
    """Production-safe default: a worker consumes the durable recording state asynchronously."""

    async def start(self, recording: Recording, upload_url: str) -> None:
        return None

    async def finish(self, recording: Recording) -> None:
        return None
