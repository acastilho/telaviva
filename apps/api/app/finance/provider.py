from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Mapping, Protocol
from uuid import UUID

from app.finance.models import PixPaymentStatus


class InvalidWebhookError(Exception):
    pass


@dataclass(frozen=True)
class PixChargeRequest:
    charge_id: UUID
    amount: Decimal
    currency: str
    description: str


@dataclass(frozen=True)
class ProviderCharge:
    reference: str
    pix_copy_paste: str
    expires_at: datetime


@dataclass(frozen=True)
class ProviderWebhookEvent:
    event_id: str
    charge_reference: str
    status: PixPaymentStatus
    amount: Decimal
    currency: str


class PaymentProvider(Protocol):
    """Boundary implemented by each PIX gateway adapter."""

    name: str

    async def create_pix_charge(self, request: PixChargeRequest) -> ProviderCharge: ...
    async def parse_webhook(
        self, headers: Mapping[str, str], payload: bytes
    ) -> ProviderWebhookEvent: ...


class FakePaymentProvider:
    """Deterministic local adapter. It must never be enabled as a production gateway."""

    name = "fake"

    async def create_pix_charge(self, request: PixChargeRequest) -> ProviderCharge:
        reference = f"fake-{request.charge_id}"
        return ProviderCharge(
            reference,
            f"000201-TELAVIVA-{reference}-{request.amount}-{request.currency}",
            datetime.now(UTC) + timedelta(minutes=30),
        )

    async def parse_webhook(
        self, headers: Mapping[str, str], payload: bytes
    ) -> ProviderWebhookEvent:
        # A real adapter validates a gateway signature before normalizing its payload.
        if headers.get("x-fake-signature") != "development-webhook":
            raise InvalidWebhookError("invalid fake webhook signature")
        try:
            import json

            data = json.loads(payload)
            return ProviderWebhookEvent(
                str(data["event_id"]),
                str(data["charge_reference"]),
                PixPaymentStatus(data["status"]),
                Decimal(str(data["amount"])),
                str(data.get("currency", "BRL")).upper(),
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise InvalidWebhookError("invalid fake webhook payload") from error


class UnsupportedPaymentProvider:
    """Explicit seam for future gateway adapters; never silently accepts operations."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def create_pix_charge(self, request: PixChargeRequest) -> ProviderCharge:
        raise NotImplementedError(f"payment provider {self.name!r} is not configured")

    async def parse_webhook(
        self, headers: Mapping[str, str], payload: bytes
    ) -> ProviderWebhookEvent:
        raise NotImplementedError(f"payment provider {self.name!r} is not configured")
