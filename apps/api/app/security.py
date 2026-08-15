import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import Settings

logger = logging.getLogger("telaviva.security")


@dataclass
class RateLimiter:
    """Small single-process limiter. Deployments should enforce a shared limit at the edge too."""

    buckets: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str, limit: int, window: int, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        bucket = self.buckets[key]
        while bucket and bucket[0] <= current - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(current)
        return True


def _client_key(request: Request) -> str:
    # Do not trust forwarding headers here; the trusted reverse proxy should normalize the peer.
    return request.client.host if request.client else "unknown"


def _audit(event: str, request: Request, response_status: int, request_id: str) -> None:
    # Bodies, query strings, authorization values and cookies are deliberately never logged.
    logger.info(
        json.dumps(
            {
                "event": event,
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response_status,
                "client": _client_key(request),
            },
            separators=(",", ":"),
        )
    )


def install_security_middleware(app: FastAPI, settings: Settings) -> None:
    limiter = RateLimiter()
    production = settings.app_env.lower() in {"production", "prod"}
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def security_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", "")
        if not request_id.isascii() or not request_id.isalnum() or len(request_id) > 64:
            request_id = uuid4().hex

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > settings.max_request_body_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = JSONResponse(
                    {"detail": "Request body too large"},
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
                _audit("request_rejected", request, response.status_code, request_id)
                return _secure(response, request_id, production)

        auth_route = request.url.path in {
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/password-recovery",
            "/auth/password-reset",
        }
        limit = settings.auth_rate_limit_requests if auth_route else settings.rate_limit_requests
        scope = request.url.path if auth_route else "api"
        key = f"{_client_key(request)}:{scope}"
        if not limiter.allow(key, limit, settings.rate_limit_window_seconds):
            response = JSONResponse(
                {"detail": "Too many requests"},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
            _audit("rate_limit_exceeded", request, response.status_code, request_id)
            return _secure(response, request_id, production)

        started = time.monotonic()
        response = await call_next(request)
        response = _secure(response, request_id, production)
        if request.method not in {"GET", "HEAD", "OPTIONS"} or response.status_code in {401, 403}:
            _audit("security_audit", request, response.status_code, request_id)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response


def _secure(response: Response, request_id: str, production: bool) -> Response:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; "
        "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' https://fastapi.tiangolo.com data:; connect-src 'self'"
    )
    if production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response
