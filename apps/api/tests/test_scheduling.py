from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.main import app
from app.scheduling.models import Notification, NotificationKind, ScheduledStream
from app.scheduling.repository import (
    InvalidReminderTimeError,
    StreamNotFoundError,
    UnknownCategoryError,
)
from app.scheduling.routes import get_scheduling_repository


CATEGORY_ID = UUID("00000000-0000-4000-8000-000000000001")
creator = User(uuid4(), "creator@example.com", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "viewer@example.com", "hash", Role.VIEWER, datetime.now(UTC))


class MemorySchedulingRepository:
    def __init__(self) -> None:
        self.streams: dict[UUID, ScheduledStream] = {}
        self.follows: set[tuple[UUID, UUID]] = set()
        self.reminders: dict[tuple[UUID, UUID], tuple[datetime, bool]] = {}
        self.notifications: dict[UUID, Notification] = {}

    async def create_stream(self, creator_id: UUID, **values: object) -> ScheduledStream:
        if values["category_id"] != CATEGORY_ID:
            raise UnknownCategoryError
        stream = ScheduledStream(
            id=uuid4(), creator_id=creator_id, created_at=datetime.now(UTC), **values  # type: ignore[arg-type]
        )
        self.streams[stream.id] = stream
        for follower_id, followed_id in self.follows:
            if followed_id == creator_id:
                notification = Notification(
                    uuid4(), follower_id, NotificationKind.STREAM_SCHEDULED,
                    "Nova aula agendada", stream.title,
                    {"stream_id": str(stream.id), "creator_id": str(creator_id)},
                    datetime.now(UTC), None,
                )
                self.notifications[notification.id] = notification
        return stream

    async def list_streams(
        self, *, creator_id: UUID | None, starts_after: datetime
    ) -> list[ScheduledStream]:
        return sorted(
            (
                stream for stream in self.streams.values()
                if stream.starts_at >= starts_after
                and (creator_id is None or stream.creator_id == creator_id)
            ),
            key=lambda stream: stream.starts_at,
        )

    async def follow(self, user_id: UUID, creator_id: UUID) -> None:
        if creator_id != creator.id:
            raise StreamNotFoundError
        self.follows.add((user_id, creator_id))

    async def unfollow(self, user_id: UUID, creator_id: UUID) -> None:
        self.follows.discard((user_id, creator_id))

    async def list_agenda(
        self, user_id: UUID, starts_after: datetime
    ) -> list[ScheduledStream]:
        return sorted(
            (
                stream for stream in self.streams.values()
                if stream.starts_at >= starts_after
                and (
                    (user_id, stream.creator_id) in self.follows
                    or (user_id, stream.id) in self.reminders
                )
            ),
            key=lambda stream: stream.starts_at,
        )

    async def add_reminder(
        self, user_id: UUID, stream_id: UUID, minutes_before: int
    ) -> datetime:
        stream = self.streams.get(stream_id)
        if stream is None:
            raise StreamNotFoundError
        notify_at = stream.starts_at - timedelta(minutes=minutes_before)
        if notify_at <= datetime.now(UTC):
            raise InvalidReminderTimeError
        self.reminders[(user_id, stream_id)] = (notify_at, False)
        return notify_at

    async def remove_reminder(self, user_id: UUID, stream_id: UUID) -> None:
        self.reminders.pop((user_id, stream_id), None)

    async def list_notifications(
        self, user_id: UUID, unread_only: bool
    ) -> list[Notification]:
        for key, (notify_at, delivered) in list(self.reminders.items()):
            if key[0] == user_id and not delivered and notify_at <= datetime.now(UTC):
                stream = self.streams[key[1]]
                notification = Notification(
                    uuid4(), user_id, NotificationKind.STREAM_REMINDER,
                    "A aula começa em breve", stream.title,
                    {"stream_id": str(stream.id)}, datetime.now(UTC), None,
                )
                self.notifications[notification.id] = notification
                self.reminders[key] = (notify_at, True)
        return sorted(
            (
                item for item in self.notifications.values()
                if item.user_id == user_id and (not unread_only or item.read_at is None)
            ),
            key=lambda item: item.created_at,
            reverse=True,
        )

    async def mark_notification_read(self, user_id: UUID, notification_id: UUID) -> bool:
        item = self.notifications.get(notification_id)
        if item is None or item.user_id != user_id:
            return False
        self.notifications[item.id] = Notification(
            item.id, item.user_id, item.kind, item.title, item.body, item.data,
            item.created_at, item.read_at or datetime.now(UTC),
        )
        return True


repository = MemorySchedulingRepository()
current_user = creator
client = TestClient(app)


def setup_function() -> None:
    global repository, current_user
    repository = MemorySchedulingRepository()
    current_user = creator
    app.dependency_overrides[get_scheduling_repository] = lambda: repository
    app.dependency_overrides[get_current_user] = lambda: current_user


def teardown_function() -> None:
    app.dependency_overrides.clear()


def stream_body(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": " APIs ao vivo ",
        "description": "Construção de uma API real",
        "objective": "Publicar um endpoint seguro",
        "starts_at": (datetime.now(UTC) + timedelta(hours=3)).isoformat(),
        "estimated_duration_minutes": 90,
        "category_id": str(CATEGORY_ID),
        "level": "INTERMEDIATE",
        "price": "29.90",
        "access_type": "PAID",
    }
    body.update(changes)
    return body


def create_stream(**changes: object) -> dict[str, object]:
    response = client.post("/streams", json=stream_body(**changes))
    assert response.status_code == 201
    return response.json()


def test_creator_schedules_and_public_can_filter_upcoming_streams() -> None:
    created = create_stream()
    assert created["title"] == "APIs ao vivo"
    assert created["price"] == "29.90"
    assert created["level"] == "INTERMEDIATE"

    response = client.get("/streams", params={"creator_id": str(creator.id)})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [created["id"]]


def test_stream_validation_and_creator_authorization() -> None:
    global current_user
    assert client.post("/streams", json=stream_body(starts_at="2020-01-01T10:00:00Z")).status_code == 422
    assert client.post("/streams", json=stream_body(starts_at="2030-01-01T10:00:00")).status_code == 422
    assert client.post("/streams", json=stream_body(access_type="FREE", price="1.00")).status_code == 422
    assert client.post("/streams", json=stream_body(access_type="PAID", price="0")).status_code == 422
    assert client.post("/streams", json=stream_body(category_id=str(uuid4()))).status_code == 422
    current_user = viewer
    assert client.post("/streams", json=stream_body()).status_code == 403


def test_following_builds_agenda_and_receives_new_stream_notification() -> None:
    global current_user
    current_user = viewer
    assert client.put(f"/creators/{creator.id}/follow").status_code == 204
    current_user = creator
    created = create_stream()
    current_user = viewer

    agenda = client.get("/agenda/me")
    assert agenda.status_code == 200
    assert [item["id"] for item in agenda.json()] == [created["id"]]
    notices = client.get("/notifications")
    assert notices.status_code == 200
    assert notices.json()[0]["kind"] == "STREAM_SCHEDULED"

    assert client.delete(f"/creators/{creator.id}/follow").status_code == 204
    assert client.get("/agenda/me").json() == []


def test_reminder_is_idempotent_delivered_once_and_can_be_read() -> None:
    global current_user
    created = create_stream(price="0", access_type="FREE", starts_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat())
    current_user = viewer
    stream_id = created["id"]
    reminder = client.put(f"/streams/{stream_id}/reminder", json={"minutes_before": 30})
    assert reminder.status_code == 200
    assert client.put(f"/streams/{stream_id}/reminder", json={"minutes_before": 30}).status_code == 200
    key = (viewer.id, UUID(str(stream_id)))
    repository.reminders[key] = (datetime.now(UTC) - timedelta(seconds=1), False)

    first = client.get("/notifications", params={"unread_only": True})
    second = client.get("/notifications", params={"unread_only": True})
    assert len(first.json()) == len(second.json()) == 1
    notification_id = first.json()[0]["id"]
    assert first.json()[0]["kind"] == "STREAM_REMINDER"
    assert client.patch(f"/notifications/{notification_id}/read").status_code == 204
    assert client.get("/notifications", params={"unread_only": True}).json() == []
    assert client.patch(f"/notifications/{uuid4()}/read").status_code == 404


def test_reminder_errors_and_authentication_are_enforced() -> None:
    global current_user
    created = create_stream(starts_at=(datetime.now(UTC) + timedelta(minutes=10)).isoformat())
    current_user = viewer
    assert client.put(f"/streams/{created['id']}/reminder", json={"minutes_before": 30}).status_code == 422
    assert client.put(f"/streams/{uuid4()}/reminder", json={}).status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/agenda/me").status_code == 401
