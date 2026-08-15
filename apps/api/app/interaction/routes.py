import asyncio
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.commerce.repository import CommerceRepository
from app.commerce.routes import get_commerce_repository
from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.repository import IdentityRepository
from app.identity.routes import get_current_user, get_identity_repository
from app.identity.security import InvalidTokenError, decode_token
from app.interaction.models import InteractionKind, InteractionSettings, ModerationAction
from app.interaction.repository import EventNotFoundError, InteractionRepository, PostgresInteractionRepository
from app.interaction.schemas import EventResponse, ModerationCreate, ReportCreate, ReportResponse, SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/streams/{stream_id}", tags=["interaction"])


def get_interaction_repository(settings: Settings = Depends(get_settings)) -> InteractionRepository:
    return PostgresInteractionRepository(settings)


class RateLimiter:
    def __init__(self, maximum: int = 8, window_seconds: int = 10) -> None:
        self.maximum = maximum
        self.window = timedelta(seconds=window_seconds)
        self._requests: dict[tuple[UUID, UUID], deque[datetime]] = defaultdict(deque)

    def allow(self, stream_id: UUID, user_id: UUID) -> bool:
        now = datetime.now(UTC)
        requests = self._requests[(stream_id, user_id)]
        while requests and now - requests[0] >= self.window:
            requests.popleft()
        if len(requests) >= self.maximum:
            return False
        requests.append(now)
        return True


class ConnectionHub:
    def __init__(self) -> None:
        self.connections: dict[UUID, dict[WebSocket, UUID]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def connect(self, stream_id: UUID, user_id: UUID, socket: WebSocket) -> int:
        await socket.accept()
        async with self._lock:
            self.connections[stream_id][socket] = user_id
            return len(self.connections[stream_id])

    async def disconnect(self, stream_id: UUID, socket: WebSocket) -> int:
        async with self._lock:
            self.connections[stream_id].pop(socket, None)
            return len(self.connections[stream_id])

    async def broadcast(self, stream_id: UUID, payload: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for socket in list(self.connections[stream_id]):
            try:
                await socket.send_json(payload)
            except (RuntimeError, WebSocketDisconnect):
                stale.append(socket)
        for socket in stale:
            await self.disconnect(stream_id, socket)

    async def remove_user(self, stream_id: UUID, user_id: UUID) -> None:
        for socket, connected_user in list(self.connections[stream_id].items()):
            if connected_user == user_id:
                await socket.close(code=1008, reason="Banned by moderator")
                await self.disconnect(stream_id, socket)


hub = ConnectionHub()
limiter = RateLimiter()


async def _owner_or_admin(stream_id: UUID, user: User, repository: InteractionRepository) -> None:
    creator_id = await repository.stream_creator(stream_id)
    if creator_id is None:
        raise HTTPException(404, "Stream not found")
    if creator_id != user.id and user.role != Role.ADMIN:
        raise HTTPException(403, "Only the creator or an admin can moderate")


@router.get("/interaction-settings", response_model=SettingsResponse)
async def settings(stream_id: UUID, repository: InteractionRepository = Depends(get_interaction_repository)) -> InteractionSettings:
    result = await repository.get_settings(stream_id)
    if result is None:
        raise HTTPException(404, "Stream not found")
    return result


@router.put("/interaction-settings", response_model=SettingsResponse)
async def update_settings(stream_id: UUID, body: SettingsUpdate, repository: InteractionRepository = Depends(get_interaction_repository), user: User = Depends(get_current_user)) -> InteractionSettings:
    await _owner_or_admin(stream_id, user, repository)
    result = await repository.update_settings(stream_id, InteractionSettings(stream_id, **body.model_dump()))
    await hub.broadcast(stream_id, {"type": "settings", **SettingsResponse.model_validate(result).model_dump(mode="json")})
    return result


@router.get("/events", response_model=list[EventResponse])
async def events(stream_id: UUID, limit: int = 50, repository: InteractionRepository = Depends(get_interaction_repository), _: User = Depends(get_current_user)) -> list[object]:
    if not 1 <= limit <= 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    if await repository.get_settings(stream_id) is None:
        raise HTTPException(404, "Stream not found")
    return list(await repository.recent_events(stream_id, limit))


@router.post("/moderation", status_code=status.HTTP_204_NO_CONTENT)
async def moderate(stream_id: UUID, body: ModerationCreate, repository: InteractionRepository = Depends(get_interaction_repository), user: User = Depends(get_current_user)) -> None:
    await _owner_or_admin(stream_id, user, repository)
    if body.user_id == user.id:
        raise HTTPException(422, "Moderators cannot restrict themselves")
    await repository.moderate(stream_id, body.user_id, user.id, body.action, body.duration_minutes)
    await hub.broadcast(stream_id, {"type": "moderation", "user_id": str(body.user_id), "action": body.action.value})
    if body.action is ModerationAction.BAN:
        await hub.remove_user(stream_id, body.user_id)


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def report(stream_id: UUID, body: ReportCreate, repository: InteractionRepository = Depends(get_interaction_repository), user: User = Depends(get_current_user)) -> object:
    try:
        return await repository.report(stream_id, user.id, body.event_id, body.reason.strip())
    except EventNotFoundError as error:
        raise HTTPException(404, "Event not found") from error


@router.websocket("/live")
async def live(stream_id: UUID, socket: WebSocket, repository: InteractionRepository = Depends(get_interaction_repository), commerce: CommerceRepository = Depends(get_commerce_repository), identities: IdentityRepository = Depends(get_identity_repository), configuration: Settings = Depends(get_settings)) -> None:
    await socket.accept()
    try:
        authentication = await asyncio.wait_for(socket.receive_json(), timeout=10)
        token = authentication.get("token") if authentication.get("type") == "authenticate" else None
        if not isinstance(token, str):
            raise InvalidTokenError
        payload = decode_token(token, "access", configuration)
        user = await identities.get_user_by_id(UUID(payload["sub"]))
        if user is None or user.role.value != payload.get("role"):
            raise InvalidTokenError
        configured = await repository.get_settings(stream_id)
        if configured is None:
            await socket.close(code=1008, reason="Access denied")
            return
        access = await commerce.check_access(stream_id, user.id)
        if not access.granted or await repository.restriction(stream_id, user.id) is ModerationAction.BAN:
            await socket.close(code=1008, reason="Access denied")
            return
    except (InvalidTokenError, TimeoutError, ValueError, KeyError):
        await socket.close(code=1008, reason="Authentication failed")
        return

    # ConnectionHub normally accepts sockets itself; authentication requires accepting first.
    async with hub._lock:
        hub.connections[stream_id][socket] = user.id
        viewers = len(hub.connections[stream_id])
    await socket.send_json({"type": "ready", "settings": SettingsResponse.model_validate(configured).model_dump(mode="json")})
    await hub.broadcast(stream_id, {"type": "viewer_count", "count": viewers})
    try:
        while True:
            incoming = await socket.receive_json()
            if incoming.get("type") not in {"message", "question", "reaction"}:
                await socket.send_json({"type": "error", "code": "invalid_event"})
                continue
            kind = InteractionKind(incoming["type"])
            content = incoming.get("content")
            configured = await repository.get_settings(stream_id)
            enabled = configured and {InteractionKind.MESSAGE: configured.chat_enabled, InteractionKind.QUESTION: configured.questions_enabled, InteractionKind.REACTION: configured.reactions_enabled}[kind]
            restriction = await repository.restriction(stream_id, user.id)
            if not enabled or restriction is not None:
                await socket.send_json({"type": "error", "code": "interaction_disabled" if not enabled else "restricted"})
            elif not isinstance(content, str) or not 1 <= len(content.strip()) <= (20 if kind is InteractionKind.REACTION else 500):
                await socket.send_json({"type": "error", "code": "invalid_content"})
            elif not limiter.allow(stream_id, user.id):
                await socket.send_json({"type": "error", "code": "rate_limited"})
            else:
                event = await repository.add_event(stream_id, user.id, kind, content.strip())
                await hub.broadcast(stream_id, {"type": "event", **EventResponse.model_validate(event).model_dump(mode="json")})
    except (WebSocketDisconnect, RuntimeError):
        viewers = await hub.disconnect(stream_id, socket)
        await hub.broadcast(stream_id, {"type": "viewer_count", "count": viewers})
