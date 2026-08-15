from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.commerce.models import AccessDecision
from app.commerce.routes import get_commerce_repository
from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.main import app
from app.recordings.models import Recording, RecordingStatus
from app.recordings.processor import RecordingProcessor
from app.recordings.repository import InvalidRecordingTransitionError
from app.recordings.routes import (
    get_recording_processor,
    get_recording_repository,
    get_recording_storage,
)

creator = User(uuid4(), "creator@record.test", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "viewer@record.test", "hash", Role.VIEWER, datetime.now(UTC))
admin = User(uuid4(), "admin@record.test", "hash", Role.ADMIN, datetime.now(UTC))
stream_id = uuid4()


class MemoryRecordingRepository:
    def __init__(self) -> None:
        self.recording: Recording | None = None

    async def stream_creator(self, selected: UUID) -> UUID | None:
        return creator.id if selected == stream_id else None

    async def get_for_stream(self, selected: UUID) -> Recording | None:
        return self.recording if selected == stream_id else None

    async def start(self, selected: UUID, source_key: str) -> Recording:
        if self.recording:
            return self.recording
        now = datetime.now(UTC)
        self.recording = Recording(
            uuid4(), selected, RecordingStatus.RECORDING, source_key, None, None,
            now, None, None, {}, None, now, now,
        )
        return self.recording

    async def stop(self, selected: UUID) -> Recording:
        if not self.recording or self.recording.status is not RecordingStatus.RECORDING:
            raise InvalidRecordingTransitionError
        self.recording = replace(
            self.recording, status=RecordingStatus.PROCESSING,
            ended_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        return self.recording

    async def complete(
        self, recording_id: UUID, playback_key: str, thumbnail_key: str,
        duration_seconds: int, metadata: dict[str, object],
    ) -> Recording:
        if (
            not self.recording
            or self.recording.id != recording_id
            or self.recording.status is not RecordingStatus.PROCESSING
        ):
            raise InvalidRecordingTransitionError
        self.recording = replace(
            self.recording, status=RecordingStatus.READY, playback_key=playback_key,
            thumbnail_key=thumbnail_key, duration_seconds=duration_seconds,
            metadata=metadata, updated_at=datetime.now(UTC),
        )
        return self.recording

    async def fail(self, recording_id: UUID, reason: str) -> Recording:
        if not self.recording or self.recording.id != recording_id:
            raise InvalidRecordingTransitionError
        self.recording = replace(
            self.recording, status=RecordingStatus.FAILED, failure_reason=reason,
            updated_at=datetime.now(UTC),
        )
        return self.recording


class MemoryStorage:
    def upload_url(self, key: str, content_type: str, expires_in: int) -> str:
        return f"https://storage.test/upload/{key}"

    def download_url(self, key: str, expires_in: int) -> str:
        return f"https://storage.test/download/{key}?ttl={expires_in}"

    def delete(self, key: str) -> None:
        return None


class SpyProcessor(RecordingProcessor):
    def __init__(self) -> None:
        self.started: list[tuple[UUID, str]] = []
        self.finished: list[UUID] = []

    async def start(self, recording: Recording, upload_url: str) -> None:
        self.started.append((recording.id, upload_url))

    async def finish(self, recording: Recording) -> None:
        self.finished.append(recording.id)


class CommerceAccess:
    def __init__(self) -> None:
        self.granted = True

    async def check_access(self, selected: UUID, user_id: UUID) -> AccessDecision:
        return AccessDecision(
            selected, user_id, self.granted, "FREE" if self.granted else "ENTITLEMENT_REQUIRED",
            None, datetime.now(UTC),
        )


repository = MemoryRecordingRepository()
storage = MemoryStorage()
processor = SpyProcessor()
commerce = CommerceAccess()
current_user = creator
client = TestClient(app)


def setup_function() -> None:
    global repository, processor, commerce, current_user
    repository = MemoryRecordingRepository()
    processor = SpyProcessor()
    commerce = CommerceAccess()
    current_user = creator
    app.dependency_overrides[get_recording_repository] = lambda: repository
    app.dependency_overrides[get_recording_storage] = lambda: storage
    app.dependency_overrides[get_recording_processor] = lambda: processor
    app.dependency_overrides[get_commerce_repository] = lambda: commerce
    app.dependency_overrides[get_current_user] = lambda: current_user


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_broadcast_automatically_starts_and_stops_recording() -> None:
    started = client.post(f"/streams/{stream_id}/broadcast/start")
    assert started.status_code == 200
    assert started.json()["status"] == "RECORDING"
    assert processor.started[0][0] == UUID(started.json()["id"])
    assert "/upload/streams/" in processor.started[0][1]
    repeated = client.post(f"/streams/{stream_id}/broadcast/start")
    assert repeated.json()["id"] == started.json()["id"]
    assert len(processor.started) == 1

    ended = client.post(f"/streams/{stream_id}/broadcast/end")
    assert ended.status_code == 200
    assert ended.json()["status"] == "PROCESSING"
    assert ended.json()["ended_at"] is not None
    assert processor.finished == [UUID(started.json()["id"])]
    assert client.post(f"/streams/{stream_id}/broadcast/end").status_code == 409


def test_worker_completion_exposes_metadata_thumbnail_and_duration() -> None:
    recording_id = client.post(f"/streams/{stream_id}/broadcast/start").json()["id"]
    client.post(f"/streams/{stream_id}/broadcast/end")
    global current_user
    current_user = admin
    completed = client.put(f"/recordings/{recording_id}/complete", json={
        "playback_key": "ready/class.mp4",
        "thumbnail_key": "ready/class.jpg",
        "duration_seconds": 3661,
        "metadata": {"width": 1920, "height": 1080, "codec": "h264"},
    })
    assert completed.status_code == 200
    assert completed.json()["status"] == "READY"
    assert completed.json()["duration_seconds"] == 3661
    assert completed.json()["metadata"]["codec"] == "h264"

    current_user = viewer
    playback = client.get(f"/streams/{stream_id}/recording")
    assert playback.status_code == 200
    assert "/download/ready/class.mp4" in playback.json()["playback_url"]
    assert "/download/ready/class.jpg" in playback.json()["thumbnail_url"]


def test_recording_reuses_stream_commercial_access_and_control_rules() -> None:
    global current_user
    current_user = viewer
    assert client.post(f"/streams/{stream_id}/broadcast/start").status_code == 403
    current_user = creator
    client.post(f"/streams/{stream_id}/broadcast/start")
    commerce.granted = False
    current_user = viewer
    assert client.get(f"/streams/{stream_id}/recording").status_code == 403
