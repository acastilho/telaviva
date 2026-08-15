from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.creators.models import Category, CreatorProfile
from app.creators.repository import UnknownCategoryError
from app.creators.routes import get_creator_repository
from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.main import app


CATEGORIES = [
    Category(UUID(int=index), slug, name)
    for index, (slug, name) in enumerate(
        [
            ("programacao", "Programação"), ("ia", "IA"), ("design", "Design"),
            ("edicao-de-video", "Edição de vídeo"), ("marketing", "Marketing"),
            ("dados", "Dados"), ("producao-musical", "Produção musical"), ("cad", "CAD"),
            ("arquitetura", "Arquitetura"), ("seguranca", "Segurança"),
            ("planilhas", "Planilhas"), ("automacao", "Automação"), ("games", "Games"),
            ("suporte-tecnico", "Suporte técnico"), ("educacao", "Educação"),
            ("mentoria", "Mentoria"),
        ],
        start=1,
    )
]


class MemoryCreatorRepository:
    def __init__(self) -> None:
        self.profiles: dict[UUID, CreatorProfile] = {}

    async def list_categories(self) -> list[Category]:
        return sorted(CATEGORIES, key=lambda item: item.name)

    async def get_profile(self, user_id: UUID) -> CreatorProfile | None:
        return self.profiles.get(user_id)

    async def upsert_profile(self, user_id: UUID, **values: object) -> CreatorProfile:
        category_ids = values.pop("category_ids")
        assert isinstance(category_ids, list)
        categories = [category for category in CATEGORIES if category.id in category_ids]
        if len(categories) != len(category_ids):
            raise UnknownCategoryError
        profile = CreatorProfile(  # type: ignore[arg-type]
            user_id=user_id, categories=categories, is_verified=False, **values
        )
        self.profiles[user_id] = profile
        return profile


repository = MemoryCreatorRepository()
creator = User(uuid4(), "creator@example.com", "hash", Role.CREATOR, datetime.now(UTC))
client = TestClient(app)


def setup_function() -> None:
    global repository
    repository = MemoryCreatorRepository()
    app.dependency_overrides[get_creator_repository] = lambda: repository
    app.dependency_overrides[get_current_user] = lambda: creator


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_lists_all_initial_categories() -> None:
    response = client.get("/categories")
    assert response.status_code == 200
    assert len(response.json()) == 16
    assert {item["slug"] for item in response.json()} == {item.slug for item in CATEGORIES}


def test_creator_can_create_update_and_publish_profile() -> None:
    body = {
        "photo_url": "https://example.com/photo.jpg",
        "name": "  Ada Criadora  ",
        "bio": "Ensino enquanto construo.",
        "profession": "  Engenheira de software  ",
        "specialties": ["Python", "APIs"],
        "tools": ["VS Code"],
        "languages": ["Português", "Inglês"],
        "category_ids": [str(CATEGORIES[0].id), str(CATEGORIES[1].id)],
        "social_links": {"github": "https://github.com/ada"},
        "default_price": "49.90",
        "accepts_tips": True,
    }
    response = client.put("/creators/me", json=body)
    assert response.status_code == 200
    assert response.json()["name"] == "Ada Criadora"
    assert response.json()["profession"] == "Engenheira de software"
    assert response.json()["default_price"] == "49.90"
    assert response.json()["accepts_tips"] is True
    assert response.json()["is_verified"] is False
    assert [item["slug"] for item in response.json()["categories"]] == ["programacao", "ia"]

    public = client.get(f"/creators/{creator.id}")
    assert public.status_code == 200
    assert public.json() == response.json()

    body["bio"] = "Bio atualizada"
    body["default_price"] = None
    updated = client.put("/creators/me", json=body)
    assert updated.status_code == 200
    assert updated.json()["bio"] == "Bio atualizada"
    assert updated.json()["default_price"] is None


def test_profile_validates_categories_urls_lists_and_price() -> None:
    base = {"name": "Ada", "profession": "Dev"}
    assert client.put(
        "/creators/me", json={**base, "category_ids": [str(uuid4())]}
    ).status_code == 422
    assert client.put(
        "/creators/me", json={**base, "social_links": {"site": "not-a-url"}}
    ).status_code == 422
    assert client.put(
        "/creators/me", json={**base, "specialties": ["Python", "python"]}
    ).status_code == 422
    assert client.put(
        "/creators/me", json={**base, "default_price": "-0.01"}
    ).status_code == 422


def test_only_creators_can_write_and_missing_profile_is_404() -> None:
    viewer = User(uuid4(), "viewer@example.com", "hash", Role.VIEWER, datetime.now(UTC))
    app.dependency_overrides[get_current_user] = lambda: viewer
    denied = client.put("/creators/me", json={"name": "Viewer", "profession": "Aluno"})
    assert denied.status_code == 403
    assert client.get(f"/creators/{uuid4()}").status_code == 404


def test_verification_status_cannot_be_self_assigned() -> None:
    response = client.put(
        "/creators/me",
        json={"name": "Ada", "profession": "Dev", "is_verified": True},
    )
    assert response.status_code == 422
    assert creator.id not in repository.profiles


def test_null_price_is_distinct_from_free_price() -> None:
    response = client.put(
        "/creators/me",
        json={"name": "Ada", "profession": "Dev", "default_price": "0.00"},
    )
    assert response.status_code == 200
    assert repository.profiles[creator.id].default_price == Decimal("0.00")
