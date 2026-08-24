from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ProductKind(StrEnum):
    CLASS = "CLASS"
    SUBSCRIPTION = "SUBSCRIPTION"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class EntitlementKind(StrEnum):
    STREAM = "STREAM"
    CREATOR_SUBSCRIPTION = "CREATOR_SUBSCRIPTION"


@dataclass(frozen=True)
class Product:
    id: UUID
    creator_id: UUID
    kind: ProductKind
    stream_id: UUID | None
    name: str
    price: Decimal
    currency: str
    subscription_days: int | None
    active: bool
    created_at: datetime


@dataclass(frozen=True)
class Order:
    id: UUID
    user_id: UUID
    product_id: UUID
    amount: Decimal
    currency: str
    status: OrderStatus
    created_at: datetime


@dataclass(frozen=True)
class Payment:
    id: UUID
    order_id: UUID
    provider: str
    provider_reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    created_at: datetime


@dataclass(frozen=True)
class Entitlement:
    id: UUID
    user_id: UUID
    kind: EntitlementKind
    resource_id: UUID
    source_order_id: UUID | None
    starts_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class AccessDecision:
    stream_id: UUID
    user_id: UUID
    granted: bool
    reason: str
    entitlement_id: UUID | None
    checked_at: datetime
    # Only populated by the authenticated access check after authorization succeeds.
    live_room_id: str | None = None
