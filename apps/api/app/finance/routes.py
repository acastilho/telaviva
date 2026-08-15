from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.finance.models import CreatorBalance, FinancialEntry, PixCharge, Withdrawal
from app.finance.provider import FakePaymentProvider, InvalidWebhookError, PaymentProvider
from app.finance.repository import (
    FinanceRepository,
    FinancialResourceNotFoundError,
    InsufficientBalanceError,
    InvalidFinancialOperationError,
    PostgresFinanceRepository,
)
from app.finance.schemas import (
    BalanceResponse,
    FinancialEntryResponse,
    PixChargeCreate,
    PixChargeResponse,
    WithdrawalCreate,
    WithdrawalResponse,
)
from app.finance.service import FinanceService
from app.identity.models import Role, User
from app.identity.routes import get_current_user, require_roles

router = APIRouter(tags=["finance"])


def get_finance_repository(settings: Settings = Depends(get_settings)) -> FinanceRepository:
    return PostgresFinanceRepository(settings)


def get_payment_provider(settings: Settings = Depends(get_settings)) -> PaymentProvider:
    if settings.payment_provider != "fake" or settings.app_env.lower() in {"production", "prod"}:
        raise HTTPException(503, "Payment provider is not configured")
    return FakePaymentProvider()


def get_finance_service(
    repository: FinanceRepository = Depends(get_finance_repository),
    provider: PaymentProvider = Depends(get_payment_provider),
    settings: Settings = Depends(get_settings),
) -> FinanceService:
    return FinanceService(repository, provider, settings.platform_fee_rate)


@router.post("/pix/charges", response_model=PixChargeResponse, status_code=201)
async def create_pix_charge(
    body: PixChargeCreate,
    service: FinanceService = Depends(get_finance_service),
    user: User = Depends(get_current_user),
) -> PixCharge:
    try:
        return await service.create_charge(user.id, **body.model_dump())
    except FinancialResourceNotFoundError as error:
        raise HTTPException(404, "Creator or pending class order not found") from error


@router.post("/pix/webhooks/{provider_name}", response_model=PixChargeResponse)
async def receive_pix_webhook(
    provider_name: str,
    request: Request,
    x_fake_signature: Annotated[str | None, Header()] = None,
    repository: FinanceRepository = Depends(get_finance_repository),
    provider: PaymentProvider = Depends(get_payment_provider),
    settings: Settings = Depends(get_settings),
) -> PixCharge:
    if provider_name != provider.name:
        raise HTTPException(404, "Payment provider not found")
    try:
        event = await provider.parse_webhook(
            {"x-fake-signature": x_fake_signature or ""}, await request.body()
        )
        return await repository.apply_webhook(
            provider.name, event, settings.platform_fee_rate
        )
    except InvalidWebhookError as error:
        raise HTTPException(401, "Invalid webhook") from error
    except FinancialResourceNotFoundError as error:
        raise HTTPException(404, "PIX charge not found") from error
    except InvalidFinancialOperationError as error:
        raise HTTPException(422, "Webhook does not match the PIX charge") from error


@router.get("/pix/charges/{charge_id}", response_model=PixChargeResponse)
async def get_pix_charge(
    charge_id: UUID,
    repository: FinanceRepository = Depends(get_finance_repository),
    user: User = Depends(get_current_user),
) -> PixCharge:
    try:
        return await repository.get_charge(charge_id, user.id)
    except FinancialResourceNotFoundError as error:
        raise HTTPException(404, "PIX charge not found") from error


@router.get("/finance/balance", response_model=BalanceResponse)
async def get_balance(
    repository: FinanceRepository = Depends(get_finance_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> CreatorBalance:
    return await repository.balance(creator.id)


@router.get("/finance/history", response_model=list[FinancialEntryResponse])
async def get_history(
    repository: FinanceRepository = Depends(get_finance_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> list[FinancialEntry]:
    return await repository.history(creator.id)


@router.post("/finance/withdrawals", response_model=WithdrawalResponse, status_code=201)
async def request_withdrawal(
    body: WithdrawalCreate,
    repository: FinanceRepository = Depends(get_finance_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> Withdrawal:
    try:
        return await repository.request_withdrawal(
            creator.id, body.amount, body.destination_reference
        )
    except InsufficientBalanceError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Insufficient available balance") from error


@router.get("/finance/withdrawals", response_model=list[WithdrawalResponse])
async def list_withdrawals(
    repository: FinanceRepository = Depends(get_finance_repository),
    creator: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> list[Withdrawal]:
    return await repository.list_withdrawals(creator.id)
