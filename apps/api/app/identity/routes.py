from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.repository import (
    DuplicateEmailError,
    IdentityRepository,
    PostgresIdentityRepository,
)
from app.identity.schemas import (
    LoginRequest,
    LogoutRequest,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserRoleUpdateRequest,
)
from app.identity.security import (
    InvalidTokenError,
    create_access_token,
    create_recovery_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


class RecoveryNotifier(Protocol):
    async def send_password_recovery(self, email: str, token: str) -> None: ...


class NullRecoveryNotifier:
    """Delivery adapter placeholder; production must replace it with an email provider."""

    async def send_password_recovery(self, email: str, token: str) -> None:
        return None


def get_identity_repository(
    settings: Settings = Depends(get_settings),
) -> IdentityRepository:
    return PostgresIdentityRepository(settings)


def get_recovery_notifier() -> RecoveryNotifier:
    return NullRecoveryNotifier()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, role=user.role, audience=user.audience)


async def _tokens(user: User, repository: IdentityRepository, settings: Settings) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id, user.role.value, settings)
    refresh_token, token_id, expires_at = create_refresh_token(user.id, settings)
    await repository.store_refresh_token(token_id, user.id, hash_token(refresh_token), expires_at)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
) -> UserResponse:
    try:
        user = await repository.create_user(
            _normalize_email(str(body.email)),
            hash_password(body.password),
            Role.VIEWER,
            body.audience,
            _normalize_email(str(body.guardian_email)) if body.guardian_email else None,
        )
    except DuplicateEmailError as error:
        raise HTTPException(status_code=409, detail="Email already registered") from error
    return _response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await repository.get_user_by_email(_normalize_email(str(body.email)))
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return await _tokens(user, repository, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token, "refresh", settings)
    except InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from error
    valid = await repository.consume_refresh_token(
        UUID(payload["jti"]), hash_token(body.refresh_token)
    )
    user = await repository.get_user_by_id(UUID(payload["sub"])) if valid else None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return await _tokens(user, repository, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        payload = decode_token(body.refresh_token, "refresh", settings)
    except InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from error
    consumed = await repository.consume_refresh_token(
        UUID(payload["jti"]), hash_token(body.refresh_token)
    )
    if not consumed:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/password-recovery", status_code=status.HTTP_202_ACCEPTED)
async def password_recovery(
    body: PasswordRecoveryRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
    notifier: RecoveryNotifier = Depends(get_recovery_notifier),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user = await repository.get_user_by_email(_normalize_email(str(body.email)))
    if user is not None:
        token = create_recovery_token()
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_minutes)
        await repository.store_recovery_token(user.id, hash_token(token), expires_at)
        await notifier.send_password_recovery(user.email, token)
    return {"detail": "If the account exists, recovery instructions will be sent"}


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset(
    body: PasswordResetRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
) -> None:
    if not await repository.consume_recovery_token(
        hash_token(body.token), hash_password(body.new_password)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired recovery token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    repository: IdentityRepository = Depends(get_identity_repository),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_token(credentials.credentials, "access", settings)
    except InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid access token") from error
    user = await repository.get_user_by_id(UUID(payload["sub"]))
    if user is None or payload.get("role") != user.role.value:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return user


def require_roles(*roles: Role) -> object:
    async def role_guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return Depends(role_guard)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return _response(user)


@router.get("/users", response_model=list[UserResponse])
async def users(
    repository: IdentityRepository = Depends(get_identity_repository),
    _: User = require_roles(Role.ADMIN),  # type: ignore[assignment]
) -> list[UserResponse]:
    return [_response(user) for user in await repository.list_users()]


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    body: UserRoleUpdateRequest,
    repository: IdentityRepository = Depends(get_identity_repository),
    admin: User = require_roles(Role.ADMIN),  # type: ignore[assignment]
) -> UserResponse:
    if user_id == admin.id and body.role is not Role.ADMIN:
        raise HTTPException(status_code=400, detail="Administrators cannot remove their own admin role")
    updated = await repository.update_user_role(user_id, body.role)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _response(updated)
