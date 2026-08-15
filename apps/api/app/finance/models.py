from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PaymentPurpose(StrEnum):
    TIP = "TIP"
    CLASS_PURCHASE = "CLASS_PURCHASE"


class PixPaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"


class LedgerEntryKind(StrEnum):
    GROSS_CREDIT = "GROSS_CREDIT"
    PLATFORM_FEE = "PLATFORM_FEE"
    CREATOR_CREDIT = "CREATOR_CREDIT"
    WITHDRAWAL_DEBIT = "WITHDRAWAL_DEBIT"
    REFUND_DEBIT = "REFUND_DEBIT"


class WithdrawalStatus(StrEnum):
    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PixCharge:
    id: UUID
    payer_id: UUID
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
    updated_at: datetime


@dataclass(frozen=True)
class FinancialEntry:
    id: UUID
    creator_id: UUID
    charge_id: UUID | None
    withdrawal_id: UUID | None
    kind: LedgerEntryKind
    amount: Decimal
    currency: str
    description: str
    created_at: datetime


@dataclass(frozen=True)
class CreatorBalance:
    creator_id: UUID
    available: Decimal
    currency: str


@dataclass(frozen=True)
class Withdrawal:
    id: UUID
    creator_id: UUID
    amount: Decimal
    currency: str
    destination_reference: str
    status: WithdrawalStatus
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime
