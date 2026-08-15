from decimal import Decimal
from uuid import UUID

from app.finance.models import PaymentPurpose, PixCharge
from app.finance.provider import PaymentProvider, PixChargeRequest
from app.finance.repository import FinanceRepository


class FinanceService:
    def __init__(
        self,
        repository: FinanceRepository,
        provider: PaymentProvider,
        platform_fee_rate: Decimal,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.platform_fee_rate = platform_fee_rate

    async def create_charge(
        self,
        payer_id: UUID,
        purpose: PaymentPurpose,
        creator_id: UUID | None,
        order_id: UUID | None,
        amount: Decimal | None,
        currency: str,
    ) -> PixCharge:
        pending = await self.repository.prepare_charge(
            payer_id, purpose, creator_id, order_id, amount, currency, self.provider.name
        )
        provider_charge = await self.provider.create_pix_charge(
            request=self._provider_request(pending)
        )
        return await self.repository.activate_charge(pending.id, provider_charge)

    @staticmethod
    def _provider_request(charge: PixCharge) -> PixChargeRequest:
        return PixChargeRequest(
            charge.id, charge.amount, charge.currency, f"TelaViva {charge.purpose.value}"
        )
