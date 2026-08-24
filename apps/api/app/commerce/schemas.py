from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.commerce.models import OrderStatus, PaymentStatus, ProductKind


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ProductKind
    stream_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = "BRL"
    subscription_days: int | None = Field(default=None, ge=1, le=366)

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a three-letter ISO code")
        return value

    @model_validator(mode="after")
    def product_scope(self) -> "ProductCreate":
        if self.kind == ProductKind.CLASS and (self.stream_id is None or self.subscription_days is not None):
            raise ValueError("class products require stream_id and cannot have subscription_days")
        if self.kind == ProductKind.SUBSCRIPTION and (self.stream_id is not None or self.subscription_days is None):
            raise ValueError("subscriptions require subscription_days and cannot have stream_id")
        return self


class ProductResponse(BaseModel):
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


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    amount: Decimal
    currency: str
    status: OrderStatus
    created_at: datetime


class PaymentEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: UUID
    provider: str = Field(min_length=1, max_length=60)
    provider_reference: str = Field(min_length=1, max_length=200)
    status: PaymentStatus
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("provider", "provider_reference")
    @classmethod
    def normalized_reference(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("currency")
    @classmethod
    def normalized_currency(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("currency must be a three-letter ISO code")
        return value.upper()


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: str
    provider_reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    created_at: datetime


class AccessResponse(BaseModel):
    stream_id: UUID
    granted: bool
    reason: str
    entitlement_id: UUID | None
    checked_at: datetime
    # Authorization-sensitive: populated only after the authenticated access decision.
    live_room_id: str | None = None
