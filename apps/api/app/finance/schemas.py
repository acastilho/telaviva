from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.finance.models import (
    LedgerEntryKind,
    PaymentPurpose,
    PixPaymentStatus,
    WithdrawalStatus,
)


class PixChargeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: PaymentPurpose
    creator_id: UUID | None = None
    order_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: str = "BRL"

    @field_validator("currency")
    @classmethod
    def brl_only(cls, value: str) -> str:
        if value.upper() != "BRL":
            raise ValueError("PIX charges currently support BRL only")
        return "BRL"

    @model_validator(mode="after")
    def purpose_fields(self) -> "PixChargeCreate":
        if self.purpose == PaymentPurpose.TIP:
            if self.creator_id is None or self.amount is None or self.order_id is not None:
                raise ValueError("tips require creator_id and amount only")
        elif self.order_id is None or self.creator_id is not None or self.amount is not None:
            raise ValueError("class purchases require order_id only")
        return self


class PixChargeResponse(BaseModel):
    id: UUID
    creator_id: UUID
    purpose: PaymentPurpose
    order_id: UUID | None
    provider: str
    provider_reference: str
    status: PixPaymentStatus
    amount: Decimal
    currency: str
    pix_copy_paste: str | None
    expires_at: datetime | None
    created_at: datetime


class BalanceResponse(BaseModel):
    creator_id: UUID
    available: Decimal
    currency: str


class FinancialEntryResponse(BaseModel):
    id: UUID
    charge_id: UUID | None
    withdrawal_id: UUID | None
    kind: LedgerEntryKind
    amount: Decimal
    currency: str
    description: str
    created_at: datetime


class WithdrawalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    destination_reference: str = Field(min_length=1, max_length=200)

    @field_validator("destination_reference")
    @classmethod
    def opaque_reference(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("dest_"):
            raise ValueError("use an opaque destination token issued by the payment provider")
        return value


class WithdrawalResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    destination_reference: str
    status: WithdrawalStatus
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime
