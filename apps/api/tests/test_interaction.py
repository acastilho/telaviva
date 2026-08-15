from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.identity.models import Role, User
from app.identity.routes import get_current_user, get_identity_repository
from app.identity.security import create_access_token
from app.interaction.models import (
    InteractionEvent,
    InteractionKind,
    InteractionSettings,
    ModerationAction,
    Report,
)
from app.interaction.repository import EventNotFoundError
from app.interaction.routes import get_interaction_repository, hub, limiter
from app.main import app

creator = User(uuid4(), "creator@live.test", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "viewer@live.test", "hash", Role.VIEWER, datetime.now(UTC))
other = User(uuid4(), "other@live.test", "hash", Role.VIEWER, datetime.now(UTC))
stream_id = uuid4()


class MemoryIdentityRepository:
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return {user.id: user for user in (creator, viewer, other)}.get(user_id)


class MemoryInteractionRepository:
    def __init__(self) -> None:
        self.configuration = InteractionSettings(stream_id)
        self.events: list[InteractionEvent] = []
        self.restrictions: dict[UUID, ModerationAction] = {}
        self.reports: list[Report] = []

    async def stream_creator(self, selected: UUID) -> UUID | None:
        return creator.id if selected == stream_id else None

    async def get_settings(self, selected: UUID) -> InteractionSettings | None:
        return self.configuration if selected == stream_id else None

    async def update_settings(
        self, selected: UUID, values: InteractionSettings
    ) -> InteractionSettings:
        self.configuration = values
        return values

    async def restriction(self, selected: UUID, user_id: UUID) -> ModerationAction | None:
        return self.restrictions.get(user_id)

    async def add_event(
        self, selected: UUID, user_id: UUID, kind: InteractionKind, content: str
    ) -> InteractionEvent:
        event = InteractionEvent(
            uuid4(), selected, user_id, kind, content, datetime.now(UTC)
        )
        self.events.append(event)
        return event

    async def recent_events(self, selected: UUID, limit: int) -> list[InteractionEvent]:
        return self.events[-limit:]

    async def moderate(
        self,
        selected: UUID,
        user_id: UUID,
        moderator_id: UUID,
        action: ModerationAction,
        duration_minutes: int | None,
    ) -> None:
        self.restrictions[user_id] = action

    async def report(
        self, selected: UUID, reporter_id: UUID, event_id: UUID, reason: str
    ) -> Report:
        if not any(event.id == event_id and event.stream_id == selected for event in self.events):
            raise EventNotFoundError
        report = Report(
            uuid4(), selected, reporter_id, event_id, reason, datetime.now(UTC)
        )
        self.reports.append(report)
        return report


repository = MemoryInteractionRepository()
current_user = creator
client = TestClient(app)


def setup_function() -> None:
    global repository, current_user
    repository = MemoryInteractionRepository()
    current_user = creator
    hub.connections.clear()
    limiter._requests.clear()
    app.dependency_overrides[get_interaction_repository] = lambda: repository
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_identity_repository] = MemoryIdentityRepository


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_creator_configures_each_interaction_channel() -> None:
    response = client.put(
        f"/streams/{stream_id}/interaction-settings",
        json={
            "chat_enabled": False,
            "questions_enabled": True,
            "reactions_enabled": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["chat_enabled"] is False
    assert client.get(f"/streams/{stream_id}/interaction-settings").json() == response.json()

    global current_user
    current_user = viewer
    assert client.put(
        f"/streams/{stream_id}/interaction-settings", json=response.json()
    ).status_code == 403


def test_moderation_reports_and_event_history() -> None:
    event = InteractionEvent(
        uuid4(), stream_id, other.id, InteractionKind.MESSAGE, "spam", datetime.now(UTC)
    )
    repository.events.append(event)

    response = client.post(
        f"/streams/{stream_id}/moderation",
        json={"user_id": str(other.id), "action": "mute", "duration_minutes": 15},
    )
    assert response.status_code == 204
    assert repository.restrictions[other.id] is ModerationAction.MUTE

    global current_user
    current_user = viewer
    report = client.post(
        f"/streams/{stream_id}/reports",
        json={"event_id": str(event.id), "reason": "conteúdo abusivo"},
    )
    assert report.status_code == 201
    assert report.json()["reporter_id"] == str(viewer.id)
    assert client.get(f"/streams/{stream_id}/events").json()[0]["content"] == "spam"
    assert client.post(
        f"/streams/{stream_id}/reports",
        json={"event_id": str(uuid4()), "reason": "não existe"},
    ).status_code == 404


def test_websocket_authentication_messages_presence_and_rate_limit() -> None:
    token, _ = create_access_token(viewer.id, viewer.role.value, get_settings())
    limiter.maximum = 1
    with client.websocket_connect(f"/streams/{stream_id}/live") as socket:
        socket.send_json({"type": "authenticate", "token": token})
        assert socket.receive_json()["type"] == "ready"
        assert socket.receive_json() == {"type": "viewer_count", "count": 1}
        socket.send_json({"type": "message", "content": "Olá!"})
        event = socket.receive_json()
        assert event["type"] == "event"
        assert event["content"] == "Olá!"
        socket.send_json({"type": "reaction", "content": "👏"})
        assert socket.receive_json()["code"] == "rate_limited"
    limiter.maximum = 8


def test_websocket_honors_disabled_channels_and_bans() -> None:
    repository.configuration = InteractionSettings(stream_id, False, True, True)
    token, _ = create_access_token(viewer.id, viewer.role.value, get_settings())
    with client.websocket_connect(f"/streams/{stream_id}/live") as socket:
        socket.send_json({"type": "authenticate", "token": token})
        socket.receive_json()
        socket.receive_json()
        socket.send_json({"type": "message", "content": "bloqueada"})
        assert socket.receive_json()["code"] == "interaction_disabled"

    repository.restrictions[viewer.id] = ModerationAction.BAN
    with client.websocket_connect(f"/streams/{stream_id}/live") as socket:
        socket.send_json({"type": "authenticate", "token": token})
        try:
            socket.receive_json()
            raise AssertionError("banned viewer should be disconnected")
        except Exception as error:
            assert "1008" in str(error)
