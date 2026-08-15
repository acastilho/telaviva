from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.commerce.models import (
    AccessDecision,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    ProductKind,
)
from app.commerce.repository import InvalidPaymentError, ProductNotFoundError, StreamNotOwnedError
from app.commerce.routes import get_commerce_repository
from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.main import app

creator = User(uuid4(), "seller@example.com", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "buyer@example.com", "hash", Role.VIEWER, datetime.now(UTC))
admin = User(uuid4(), "admin@example.com", "hash", Role.ADMIN, datetime.now(UTC))
stream_id = uuid4()


class MemoryCommerceRepository:
    def __init__(self) -> None:
        self.products: dict[UUID, Product] = {}
        self.orders: dict[UUID, Order] = {}
        self.entitled: set[tuple[UUID, UUID]] = set()
        self.invited: set[tuple[UUID, UUID]] = set()
        self.access_type = "PAID"

    async def create_product(self, creator_id: UUID, **values: object) -> Product:
        if values["kind"] == ProductKind.CLASS and values["stream_id"] != stream_id:
            raise StreamNotOwnedError
        product = Product(uuid4(), creator_id, created_at=datetime.now(UTC), active=True, **values)  # type: ignore[arg-type]
        self.products[product.id] = product
        return product

    async def create_order(self, user_id: UUID, product_id: UUID) -> Order:
        product = self.products.get(product_id)
        if product is None:
            raise ProductNotFoundError
        order = Order(
            uuid4(), user_id, product_id, product.price, product.currency,
            OrderStatus.PENDING, datetime.now(UTC),
        )
        self.orders[order.id] = order
        return order

    async def record_payment(self, **values: object) -> Payment:
        order = self.orders[values["order_id"]]  # type: ignore[index]
        if order.amount != values["amount"] or order.currency != values["currency"]:
            raise InvalidPaymentError
        payment = Payment(uuid4(), created_at=datetime.now(UTC), **values)  # type: ignore[arg-type]
        if payment.status == PaymentStatus.SUCCEEDED:
            product = self.products[order.product_id]
            assert product.stream_id is not None
            self.entitled.add((order.user_id, product.stream_id))
        return payment

    async def invite(self, selected: UUID, creator_id: UUID, user_id: UUID) -> None:
        if selected != stream_id or creator_id != creator.id:
            raise StreamNotOwnedError
        self.invited.add((user_id, selected))

    async def check_access(self, selected: UUID, user_id: UUID) -> AccessDecision:
        granted = (
            self.access_type == "FREE" or (user_id, selected) in self.entitled
            or (self.access_type == "PRIVATE" and (user_id, selected) in self.invited)
            or user_id == creator.id
        )
        return AccessDecision(
            selected, user_id, granted, "ENTITLED" if granted else "ENTITLEMENT_REQUIRED",
            uuid4() if (user_id, selected) in self.entitled else None, datetime.now(UTC),
        )


repository = MemoryCommerceRepository()
current_user = creator
client = TestClient(app)


def setup_function() -> None:
    global repository, current_user
    repository = MemoryCommerceRepository()
    current_user = creator
    app.dependency_overrides[get_commerce_repository] = lambda: repository
    app.dependency_overrides[get_current_user] = lambda: current_user


def teardown_function() -> None:
    app.dependency_overrides.clear()


def create_class_product() -> dict[str, object]:
    response = client.post("/products", json={
        "kind": "CLASS", "stream_id": str(stream_id), "name": "Aula premium",
        "price": "39.90", "currency": "brl",
    })
    assert response.status_code == 201
    return response.json()


def test_purchase_grants_access_only_after_successful_payment() -> None:
    global current_user
    product = create_class_product()
    current_user = viewer
    assert client.post(f"/streams/{stream_id}/access").status_code == 403
    order = client.post("/orders", json={"product_id": product["id"]})
    assert order.status_code == 201
    assert order.json()["amount"] == "39.90"
    assert client.post(f"/streams/{stream_id}/access").status_code == 403

    current_user = admin
    payment = client.post("/payment-events", json={
        "order_id": order.json()["id"], "provider": "gateway-x",
        "provider_reference": "txn-123", "status": "SUCCEEDED",
        "amount": "39.90", "currency": "BRL",
    })
    assert payment.status_code == 201
    current_user = viewer
    access = client.post(f"/streams/{stream_id}/access")
    assert access.status_code == 200
    assert access.json()["granted"] is True
    assert access.json()["entitlement_id"] is not None


def test_private_stream_requires_invitation() -> None:
    global current_user
    repository.access_type = "PRIVATE"
    current_user = viewer
    assert client.post(f"/streams/{stream_id}/access").status_code == 403
    current_user = creator
    assert client.put(f"/streams/{stream_id}/invites/{viewer.id}").status_code == 204
    current_user = viewer
    assert client.post(f"/streams/{stream_id}/access").status_code == 200


def test_commerce_authorization_and_payment_validation() -> None:
    global current_user
    product = create_class_product()
    current_user = viewer
    assert client.post("/products", json={
        "kind": "CLASS", "stream_id": str(stream_id), "name": "Nope",
        "price": "1.00",
    }).status_code == 403
    order = client.post("/orders", json={"product_id": product["id"]}).json()
    assert client.post("/payment-events", json={
        "order_id": order["id"], "provider": "x", "provider_reference": "1",
        "status": "SUCCEEDED", "amount": "1.00", "currency": "BRL",
    }).status_code == 403
    current_user = admin
    assert client.post("/payment-events", json={
        "order_id": order["id"], "provider": "x", "provider_reference": "1",
        "status": "SUCCEEDED", "amount": "1.00", "currency": "BRL",
    }).status_code == 422


def test_product_shape_and_unknown_product_are_rejected() -> None:
    assert client.post("/products", json={
        "kind": "SUBSCRIPTION", "stream_id": str(stream_id), "name": "Plano",
        "price": "20.00",
    }).status_code == 422
    global current_user
    current_user = viewer
    assert client.post("/orders", json={"product_id": str(uuid4())}).status_code == 404
