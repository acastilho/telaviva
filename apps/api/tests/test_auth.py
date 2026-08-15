from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.identity.models import Role, User
from app.identity.repository import DuplicateEmailError
from app.identity.routes import get_identity_repository, get_recovery_notifier
from app.identity.security import hash_password, hash_token, verify_password
from app.main import app


class MemoryRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.refresh_tokens: dict[UUID, tuple[UUID, str, datetime, bool]] = {}
        self.recovery_tokens: dict[str, tuple[UUID, datetime, bool]] = {}

    async def create_user(self, email: str, password_hash: str, role: Role) -> User:
        if any(user.email == email for user in self.users.values()):
            raise DuplicateEmailError
        user = User(uuid4(), email, password_hash, role, datetime.now(UTC))
        self.users[user.id] = user
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def list_users(self) -> list[User]:
        return list(self.users.values())

    async def store_refresh_token(
        self, token_id: UUID, user_id: UUID, token_hash_value: str, expires_at: datetime
    ) -> None:
        self.refresh_tokens[token_id] = (user_id, token_hash_value, expires_at, False)

    async def consume_refresh_token(self, token_id: UUID, token_hash_value: str) -> bool:
        value = self.refresh_tokens.get(token_id)
        if (
            value is None
            or value[1] != token_hash_value
            or value[3]
            or value[2] <= datetime.now(UTC)
        ):
            return False
        self.refresh_tokens[token_id] = (*value[:3], True)
        return True

    async def store_recovery_token(
        self, user_id: UUID, token_hash_value: str, expires_at: datetime
    ) -> None:
        self.recovery_tokens[token_hash_value] = (user_id, expires_at, False)

    async def consume_recovery_token(self, token_hash_value: str, password_hash: str) -> bool:
        value = self.recovery_tokens.get(token_hash_value)
        if value is None or value[2] or value[1] <= datetime.now(UTC):
            return False
        user = self.users[value[0]]
        self.users[user.id] = User(user.id, user.email, password_hash, user.role, user.created_at)
        self.recovery_tokens[token_hash_value] = (*value[:2], True)
        for token_id, refresh in list(self.refresh_tokens.items()):
            if refresh[0] == user.id:
                self.refresh_tokens[token_id] = (*refresh[:3], True)
        return True


class CapturingNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def send_password_recovery(self, email: str, token: str) -> None:
        self.messages.append((email, token))


repository = MemoryRepository()
notifier = CapturingNotifier()
client = TestClient(app)


def setup_function() -> None:
    global repository, notifier
    repository = MemoryRepository()
    notifier = CapturingNotifier()
    app.dependency_overrides[get_identity_repository] = lambda: repository
    app.dependency_overrides[get_recovery_notifier] = lambda: notifier


def teardown_function() -> None:
    app.dependency_overrides.clear()


def register_and_login(
    email: str = "viewer@example.com", password: str = "strong-password-123"
) -> dict[str, str | int]:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def test_register_normalizes_email_hashes_password_and_prevents_duplicates() -> None:
    response = client.post(
        "/auth/register", json={"email": "Person@Example.COM", "password": "strong-password-123"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "person@example.com"
    assert response.json()["role"] == "VIEWER"
    user = next(iter(repository.users.values()))
    assert user.password_hash != "strong-password-123"
    assert verify_password(user.password_hash, "strong-password-123")

    duplicate = client.post(
        "/auth/register", json={"email": "person@example.com", "password": "another-password-123"}
    )
    assert duplicate.status_code == 409


def test_registration_validation_and_invalid_login() -> None:
    invalid = client.post("/auth/register", json={"email": "invalid", "password": "short"})
    assert invalid.status_code == 422
    register_and_login()
    response = client.post(
        "/auth/login", json={"email": "viewer@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_access_token_protects_me_and_refresh_rotates_once() -> None:
    tokens = register_and_login()
    access = str(tokens["access_token"])
    refresh = str(tokens["refresh_token"])
    assert client.get("/auth/me").status_code == 401
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "viewer@example.com"

    rotated = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != refresh
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_logout_revokes_refresh_token() -> None:
    tokens = register_and_login()
    refresh = str(tokens["refresh_token"])
    assert client.post("/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_rbac_denies_viewer_and_allows_admin() -> None:
    viewer_tokens = register_and_login()
    denied = client.get(
        "/auth/users", headers={"Authorization": f"Bearer {viewer_tokens['access_token']}"}
    )
    assert denied.status_code == 403

    admin = User(
        uuid4(),
        "admin@example.com",
        hash_password("admin-password-123"),
        Role.ADMIN,
        datetime.now(UTC),
    )
    repository.users[admin.id] = admin
    admin_login = client.post(
        "/auth/login", json={"email": admin.email, "password": "admin-password-123"}
    ).json()
    allowed = client.get(
        "/auth/users", headers={"Authorization": f"Bearer {admin_login['access_token']}"}
    )
    assert allowed.status_code == 200
    assert len(allowed.json()) == 2


def test_password_recovery_does_not_enumerate_and_resets_once() -> None:
    old_tokens = register_and_login()
    existing = client.post("/auth/password-recovery", json={"email": "viewer@example.com"})
    missing = client.post("/auth/password-recovery", json={"email": "missing@example.com"})
    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()
    assert len(notifier.messages) == 1

    token = notifier.messages[0][1]
    assert hash_token(token) in repository.recovery_tokens
    reset = client.post(
        "/auth/password-reset", json={"token": token, "new_password": "new-strong-password-123"}
    )
    assert reset.status_code == 204
    assert client.post(
        "/auth/password-reset", json={"token": token, "new_password": "other-strong-password-123"}
    ).status_code == 400
    assert client.post(
        "/auth/login", json={"email": "viewer@example.com", "password": "new-strong-password-123"}
    ).status_code == 200
    assert client.post(
        "/auth/refresh", json={"refresh_token": old_tokens["refresh_token"]}
    ).status_code == 401
