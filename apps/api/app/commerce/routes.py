from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.commerce.models import AccessDecision, Order, Payment, Product
from app.commerce.repository import (
    CommerceRepository,
    InvalidPaymentError,
    OrderNotFoundError,
    PostgresCommerceRepository,
    ProductNotFoundError,
    StreamNotOwnedError,
)
from app.commerce.schemas import (
    AccessResponse,
    OrderCreate,
    OrderResponse,
    PaymentEventCreate,
    PaymentResponse,
    ProductCreate,
    ProductResponse,
)
from app.config import Settings, get_settings
from app.identity.models import Role, User
from app.identity.routes import get_current_user, require_roles

router = APIRouter(tags=["commerce"])


def get_commerce_repository(settings: Settings = Depends(get_settings)) -> CommerceRepository:
    return PostgresCommerceRepository(settings)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    repository: CommerceRepository = Depends(get_commerce_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> Product:
    try:
        return await repository.create_product(creator.id, **body.model_dump())
    except StreamNotOwnedError as error:
        raise HTTPException(
            422, "CLASS products require a paid stream owned by the creator at the same price"
        ) from error


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    repository: CommerceRepository = Depends(get_commerce_repository),
    user: User = Depends(get_current_user),
) -> Order:
    try:
        return await repository.create_order(user.id, body.product_id)
    except ProductNotFoundError as error:
        raise HTTPException(404, "Product not found") from error


@router.post(
    "/payment-events", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED
)
async def record_payment_event(
    body: PaymentEventCreate,
    repository: CommerceRepository = Depends(get_commerce_repository),
    _: User = require_roles(Role.ADMIN),  # type: ignore[assignment]
) -> Payment:
    """Receive a normalized event from a verified gateway adapter."""
    try:
        return await repository.record_payment(**body.model_dump())
    except OrderNotFoundError as error:
        raise HTTPException(404, "Order not found") from error
    except InvalidPaymentError as error:
        raise HTTPException(422, "Payment amount or currency does not match the order") from error


@router.put("/streams/{stream_id}/invites/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def invite_to_stream(
    stream_id: UUID,
    user_id: UUID,
    repository: CommerceRepository = Depends(get_commerce_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> None:
    try:
        await repository.invite(stream_id, creator.id, user_id)
    except StreamNotOwnedError as error:
        raise HTTPException(404, "Stream not found") from error


@router.post("/streams/{stream_id}/access", response_model=AccessResponse)
async def enter_stream(
    stream_id: UUID,
    repository: CommerceRepository = Depends(get_commerce_repository),
    user: User = Depends(get_current_user),
) -> AccessDecision:
    try:
        decision = await repository.check_access(stream_id, user.id)
    except ProductNotFoundError as error:
        raise HTTPException(404, "Stream not found") from error
    if not decision.granted:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Entitlement or invitation required")
    return decision
