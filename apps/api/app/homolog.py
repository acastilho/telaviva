import asyncio
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.config import Settings, get_settings
from app.identity.repository import IdentityRepository
from app.identity.routes import get_identity_repository
from app.identity.security import InvalidTokenError, decode_token

router = APIRouter(prefix="/homolog", tags=["homologation"])


class HomologationHub:
    def __init__(self) -> None:
        self.connections: dict[WebSocket, UUID] = {}
        self._lock = asyncio.Lock()

    async def add(self, socket: WebSocket, user_id: UUID) -> int:
        async with self._lock:
            self.connections[socket] = user_id
            return len(self.connections)

    async def remove(self, socket: WebSocket) -> int:
        async with self._lock:
            self.connections.pop(socket, None)
            return len(self.connections)

    async def broadcast(self, payload: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for socket in list(self.connections):
            try:
                await socket.send_json(payload)
            except (RuntimeError, WebSocketDisconnect):
                stale.append(socket)
        for socket in stale:
            await self.remove(socket)


class HomologationRateLimiter:
    def __init__(self, maximum: int = 8, window_seconds: int = 10) -> None:
        self.maximum = maximum
        self.window = timedelta(seconds=window_seconds)
        self.requests: dict[UUID, deque[datetime]] = defaultdict(deque)

    def allow(self, user_id: UUID) -> bool:
        now = datetime.now(UTC)
        requests = self.requests[user_id]
        while requests and now - requests[0] >= self.window:
            requests.popleft()
        if len(requests) >= self.maximum:
            return False
        requests.append(now)
        return True


hub = HomologationHub()
limiter = HomologationRateLimiter()


async def _resolve_user_id(
    token: str,
    configuration: Settings,
    identities: IdentityRepository,
) -> UUID:
    if configuration.app_env.lower() == "homologation":
        if len(token) < 8:
            raise InvalidTokenError
        return uuid5(NAMESPACE_URL, f"instituto-tela-viva:homolog:{token}")

    payload = decode_token(token, "access", configuration)
    user = await identities.get_user_by_id(UUID(payload["sub"]))
    if user is None or user.role.value != payload.get("role"):
        raise InvalidTokenError
    return user.id


@router.websocket("/live")
async def homologation_live(
    socket: WebSocket,
    identities: IdentityRepository = Depends(get_identity_repository),
    configuration: Settings = Depends(get_settings),
) -> None:
    """Ephemeral room used only to validate live data without recording or persistence."""
    await socket.accept()
    if configuration.app_env.lower() not in {"development", "test", "homologation"}:
        await socket.close(code=1008, reason="Homologation room disabled")
        return

    try:
        authentication = await asyncio.wait_for(socket.receive_json(), timeout=10)
        token = authentication.get("token") if authentication.get("type") == "authenticate" else None
        if not isinstance(token, str):
            raise InvalidTokenError
        user_id = await _resolve_user_id(token, configuration, identities)
    except (InvalidTokenError, TimeoutError, ValueError, KeyError):
        await socket.close(code=1008, reason="Authentication failed")
        return

    viewers = await hub.add(socket, user_id)
    await socket.send_json({
        "type": "ready",
        "settings": {
            "chat_enabled": True,
            "questions_enabled": True,
            "reactions_enabled": True,
        },
        "mode": "homologation_ephemeral",
    })
    await hub.broadcast({"type": "viewer_count", "count": viewers})

    try:
        while True:
            incoming = await socket.receive_json()
            kind = incoming.get("type")
            content = incoming.get("content")
            if kind not in {"message", "question", "reaction"}:
                await socket.send_json({"type": "error", "code": "invalid_event"})
                continue
            maximum = 20 if kind == "reaction" else 500
            if not isinstance(content, str) or not 1 <= len(content.strip()) <= maximum:
                await socket.send_json({"type": "error", "code": "invalid_content"})
                continue
            if not limiter.allow(user_id):
                await socket.send_json({"type": "error", "code": "rate_limited"})
                continue
            await hub.broadcast({
                "type": "event",
                "id": str(uuid4()),
                "stream_id": "homologation",
                "user_id": str(user_id),
                "kind": kind,
                "content": content.strip(),
                "created_at": datetime.now(UTC).isoformat(),
            })
    except (WebSocketDisconnect, RuntimeError):
        viewers = await hub.remove(socket)
        await hub.broadcast({"type": "viewer_count", "count": viewers})
