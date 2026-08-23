"""End-to-end coverage for TelaViva's principal user journey.

The scenario deliberately uses the HTTP and WebSocket boundaries. Only external
infrastructure adapters (PostgreSQL, object storage and media processing) are
replaced by the same in-memory fakes used by the focused domain tests.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.commerce.routes import get_commerce_repository
from app.creators.routes import get_creator_repository
from app.finance.provider import FakePaymentProvider
from app.finance.routes import get_finance_repository, get_payment_provider
from app.identity.models import Role
from app.identity.routes import get_identity_repository
from app.interaction.routes import get_interaction_repository, hub, limiter
from app.main import app
from app.recordings.routes import (
    get_recording_processor,
    get_recording_repository,
    get_recording_storage,
)
from app.scheduling.routes import get_scheduling_repository
from tests import (
    test_auth,
    test_commerce,
    test_creators,
    test_finance,
    test_interaction,
    test_recordings,
    test_scheduling,
)


client = TestClient(app)


def _register(email: str) -> UUID:
    response = client.post(
        "/auth/register", json={"email": email, "password": "strong-password-123"}
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _login(email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login", json={"email": email, "password": "strong-password-123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_complete_live_class_journey(monkeypatch: MonkeyPatch) -> None:
    identities = test_auth.MemoryRepository()
    creators = test_creators.MemoryCreatorRepository()
    scheduling = test_scheduling.MemorySchedulingRepository()
    commerce = test_commerce.MemoryCommerceRepository()
    finance = test_finance.MemoryFinanceRepository()
    recordings = test_recordings.MemoryRecordingRepository()
    interactions = test_interaction.MemoryInteractionRepository()
    storage = test_recordings.MemoryStorage()
    processor = test_recordings.SpyProcessor()

    app.dependency_overrides.clear()
    app.dependency_overrides.update(
        {
            get_identity_repository: lambda: identities,
            get_creator_repository: lambda: creators,
            get_scheduling_repository: lambda: scheduling,
            get_commerce_repository: lambda: commerce,
            get_finance_repository: lambda: finance,
            get_payment_provider: FakePaymentProvider,
            get_recording_repository: lambda: recordings,
            get_recording_storage: lambda: storage,
            get_recording_processor: lambda: processor,
            get_interaction_repository: lambda: interactions,
        }
    )
    hub.connections.clear()
    limiter._requests.clear()

    creator_email = "creator@journey.example.com"
    viewer_email = "viewer@journey.example.com"
    admin_email = "admin@journey.example.com"

    try:
        # Cadastro e login usam o fluxo real, inclusive hash de senha e JWT.
        creator_id = _register(creator_email)
        viewer_id = _register(viewer_email)
        admin_id = _register(admin_email)
        identities.users[creator_id] = replace(identities.users[creator_id], role=Role.CREATOR)
        identities.users[admin_id] = replace(identities.users[admin_id], role=Role.ADMIN)
        creator_headers = _login(creator_email)
        viewer_headers = _login(viewer_email)
        admin_headers = _login(admin_email)
        assert identities.users[viewer_id].role is Role.VIEWER

        creator = identities.users[creator_id]
        monkeypatch.setattr(test_scheduling, "creator", creator)
        monkeypatch.setattr(test_commerce, "creator", creator)
        monkeypatch.setattr(test_finance, "creator", creator)
        monkeypatch.setattr(test_recordings, "creator", creator)
        monkeypatch.setattr(test_interaction, "creator", creator)

        # Criar perfil.
        profile = client.put(
            "/creators/me",
            headers=creator_headers,
            json={
                "name": "Ada Criadora",
                "profession": "Engenheira de software",
                "bio": "Construção de APIs ao vivo.",
                "category_ids": [str(test_creators.CATEGORIES[0].id)],
                "accepts_tips": True,
            },
        )
        assert profile.status_code == 200

        # Agendar e encontrar aula no catálogo público.
        starts_at = datetime.now(UTC) + timedelta(days=2)
        scheduled = client.post(
            "/streams",
            headers=creator_headers,
            json={
                "title": "API do zero",
                "objective": "Publicar uma API segura",
                "starts_at": starts_at.isoformat(),
                "estimated_duration_minutes": 60,
                "category_id": str(test_scheduling.CATEGORY_ID),
                "level": "BEGINNER",
                "price": "39.90",
                "access_type": "PAID",
            },
        )
        assert scheduled.status_code == 201
        stream_id = UUID(scheduled.json()["id"])
        found = client.get("/streams", params={"creator_id": str(creator_id)})
        assert [item["id"] for item in found.json()] == [str(stream_id)]

        monkeypatch.setattr(test_commerce, "stream_id", stream_id)
        monkeypatch.setattr(test_recordings, "stream_id", stream_id)
        monkeypatch.setattr(test_interaction, "stream_id", stream_id)
        interactions.configuration = replace(interactions.configuration, stream_id=stream_id)

        # Comprar acesso e validar que a sala permanece fechada até a confirmação.
        product = client.post(
            "/products",
            headers=creator_headers,
            json={
                "kind": "CLASS",
                "stream_id": str(stream_id),
                "name": "Acesso à API do zero",
                "price": "39.90",
            },
        )
        assert product.status_code == 201
        order = client.post(
            "/orders", headers=viewer_headers, json={"product_id": product.json()["id"]}
        )
        assert order.status_code == 201
        assert client.post(f"/streams/{stream_id}/access", headers=viewer_headers).status_code == 403
        payment = client.post(
            "/payment-events",
            headers=admin_headers,
            json={
                "order_id": order.json()["id"],
                "provider": "e2e-gateway",
                "provider_reference": "e2e-payment-1",
                "status": "SUCCEEDED",
                "amount": "39.90",
                "currency": "BRL",
            },
        )
        assert payment.status_code == 201
        assert client.post(f"/streams/{stream_id}/access", headers=viewer_headers).status_code == 200

        # Acessar a transmissão autenticada e participar do chat.
        viewer_token = viewer_headers["Authorization"].removeprefix("Bearer ")
        with client.websocket_connect(f"/streams/{stream_id}/live") as socket:
            socket.send_json({"type": "authenticate", "token": viewer_token})
            assert socket.receive_json()["type"] == "ready"
            assert socket.receive_json()["type"] == "viewer_count"
            socket.send_json({"type": "message", "content": "Acompanhando!"})
            assert socket.receive_json()["content"] == "Acompanhando!"

        # Enviar gorjeta e confirmar o crédito pelo webhook idempotente.
        tip = client.post(
            "/pix/charges",
            headers=viewer_headers,
            json={"purpose": "TIP", "creator_id": str(creator_id), "amount": "25.00"},
        )
        assert tip.status_code == 201
        confirmed_tip = client.post(
            "/pix/webhooks/fake",
            headers={"x-fake-signature": "development-webhook"},
            json={
                "event_id": "e2e-tip-1",
                "charge_reference": tip.json()["provider_reference"],
                "status": "SUCCEEDED",
                "amount": "25.00",
                "currency": "BRL",
            },
        )
        assert confirmed_tip.status_code == 200

        # Finalizar transmissão, gerar gravação e liberar replay.
        started = client.post(f"/streams/{stream_id}/broadcast/start", headers=creator_headers)
        assert started.status_code == 200
        recording_id = started.json()["id"]
        ended = client.post(f"/streams/{stream_id}/broadcast/end", headers=creator_headers)
        assert ended.json()["status"] == "PROCESSING"
        completed = client.put(
            f"/recordings/{recording_id}/complete",
            headers=admin_headers,
            json={
                "playback_key": "ready/e2e-class.mp4",
                "thumbnail_key": "ready/e2e-class.jpg",
                "duration_seconds": 3600,
                "metadata": {"codec": "h264"},
            },
        )
        assert completed.status_code == 200
        replay = client.get(f"/recordings/{recording_id}", headers=viewer_headers)
        assert replay.status_code == 200
        assert "ready/e2e-class.mp4" in replay.json()["playback_url"]

        # Administrar conteúdo: o administrador consulta usuários e processa mídia.
        users = client.get("/auth/users", headers=admin_headers)
        assert users.status_code == 200
        assert {item["role"] for item in users.json()} == {"VIEWER", "CREATOR", "ADMIN"}
    finally:
        app.dependency_overrides.clear()
        hub.connections.clear()
        limiter._requests.clear()
