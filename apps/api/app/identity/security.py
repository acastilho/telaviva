import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import Settings

_hasher = PasswordHasher()


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: UUID, role: str, settings: Settings) -> tuple[str, int]:
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), expires_in


def create_refresh_token(user_id: UUID, settings: Settings) -> tuple[str, UUID, datetime]:
    token_id = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "iat": datetime.now(UTC),
        "exp": expires_at,
        "jti": str(token_id),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), token_id, expires_at


def decode_token(token: str, expected_type: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                issuer=settings.jwt_issuer,
                options={"require": ["sub", "type", "exp", "iat", "jti"]},
            ),
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError from error
    if payload.get("type") != expected_type:
        raise InvalidTokenError
    try:
        UUID(payload["sub"])
        UUID(payload["jti"])
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidTokenError from error
    return payload


def create_recovery_token() -> str:
    return secrets.token_urlsafe(32)
