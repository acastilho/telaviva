from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.config import Settings
from app.finance.models import (
    CreatorBalance,
    FinancialEntry,
    LedgerEntryKind,
    PaymentPurpose,
    PixCharge,
    PixPaymentStatus,
    Withdrawal,
    WithdrawalStatus,
)
from app.finance.provider import ProviderCharge, ProviderWebhookEvent


class FinancialResourceNotFoundError(Exception):
    pass


class InvalidFinancialOperationError(Exception):
    pass


class InsufficientBalanceError(Exception):
    pass


class FinanceRepository(Protocol):
    async def prepare_charge(
        self,
        payer_id: UUID,
        purpose: PaymentPurpose,
        creator_id: UUID | None,
        order_id: UUID | None,
        amount: Decimal | None,
        currency: str,
        provider: str,
    ) -> PixCharge: ...
    async def activate_charge(self, charge_id: UUID, charge: ProviderCharge) -> PixCharge: ...
    async def get_charge(self, charge_id: UUID, payer_id: UUID) -> PixCharge: ...
    async def apply_webhook(
        self, provider: str, event: ProviderWebhookEvent, platform_fee_rate: Decimal
    ) -> PixCharge: ...
    async def balance(self, creator_id: UUID) -> CreatorBalance: ...
    async def history(self, creator_id: UUID) -> list[FinancialEntry]: ...
    async def request_withdrawal(
        self, creator_id: UUID, amount: Decimal, destination_reference: str
    ) -> Withdrawal: ...
    async def list_withdrawals(self, creator_id: UUID) -> list[Withdrawal]: ...


def _charge(row: asyncpg.Record) -> PixCharge:
    return PixCharge(
        row["id"], row["payer_id"], row["creator_id"], PaymentPurpose(row["purpose"]),
        row["order_id"], row["provider"], row["provider_reference"],
        PixPaymentStatus(row["status"]), row["amount"], row["currency"],
        row["pix_copy_paste"], row["expires_at"], row["created_at"], row["updated_at"],
    )


def _entry(row: asyncpg.Record) -> FinancialEntry:
    return FinancialEntry(
        row["id"], row["creator_id"], row["charge_id"], row["withdrawal_id"],
        LedgerEntryKind(row["kind"]), row["amount"], row["currency"], row["description"],
        row["created_at"],
    )


def _withdrawal(row: asyncpg.Record) -> Withdrawal:
    return Withdrawal(
        row["id"], row["creator_id"], row["amount"], row["currency"],
        row["destination_reference"], WithdrawalStatus(row["status"]),
        row["provider_reference"], row["created_at"], row["updated_at"],
    )


class PostgresFinanceRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def prepare_charge(
        self,
        payer_id: UUID,
        purpose: PaymentPurpose,
        creator_id: UUID | None,
        order_id: UUID | None,
        amount: Decimal | None,
        currency: str,
        provider: str,
    ) -> PixCharge:
        connection = await self._connect()
        try:
            if purpose == PaymentPurpose.CLASS_PURCHASE:
                row = await connection.fetchrow(
                    "SELECT o.amount,o.currency,p.creator_id FROM orders o "
                    "JOIN products p ON p.id=o.product_id "
                    "WHERE o.id=$1 AND o.user_id=$2 AND o.status='PENDING' AND p.kind='CLASS'",
                    order_id, payer_id,
                )
                if row is None:
                    raise FinancialResourceNotFoundError
                amount, currency, creator_id = row["amount"], row["currency"], row["creator_id"]
            elif not await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM creator_profiles WHERE user_id=$1 AND published)",
                creator_id,
            ):
                raise FinancialResourceNotFoundError
            assert creator_id is not None and amount is not None
            row = await connection.fetchrow(
                "INSERT INTO pix_charges "
                "(id,payer_id,creator_id,purpose,order_id,provider,provider_reference,status,"
                "amount,currency) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,'PENDING',$8,$9) RETURNING *",
                uuid4(), payer_id, creator_id, str(purpose), order_id, provider,
                f"pending-{uuid4()}", amount, currency,
            )
            assert row is not None
            return _charge(row)
        finally:
            await connection.close()

    async def activate_charge(self, charge_id: UUID, charge: ProviderCharge) -> PixCharge:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "UPDATE pix_charges SET provider_reference=$2,pix_copy_paste=$3,expires_at=$4," 
                "updated_at=now() WHERE id=$1 AND status='PENDING' RETURNING *",
                charge_id, charge.reference, charge.pix_copy_paste, charge.expires_at,
            )
            if row is None:
                raise FinancialResourceNotFoundError
            return _charge(row)
        finally:
            await connection.close()

    async def get_charge(self, charge_id: UUID, payer_id: UUID) -> PixCharge:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "SELECT * FROM pix_charges WHERE id=$1 AND payer_id=$2", charge_id, payer_id
            )
            if row is None:
                raise FinancialResourceNotFoundError
            return _charge(row)
        finally:
            await connection.close()

    async def apply_webhook(
        self, provider: str, event: ProviderWebhookEvent, platform_fee_rate: Decimal
    ) -> PixCharge:
        connection = await self._connect()
        try:
            async with connection.transaction():
                charge = await connection.fetchrow(
                    "SELECT * FROM pix_charges WHERE provider=$1 "
                    "AND provider_reference=$2 FOR UPDATE",
                    provider, event.charge_reference,
                )
                if charge is None:
                    raise FinancialResourceNotFoundError
                if charge["amount"] != event.amount or charge["currency"] != event.currency:
                    raise InvalidFinancialOperationError
                inserted = await connection.fetchval(
                    "INSERT INTO payment_webhook_events (provider,event_id,charge_id) "
                    "VALUES ($1,$2,$3) ON CONFLICT DO NOTHING RETURNING event_id",
                    provider, event.event_id, charge["id"],
                )
                if inserted is None:
                    return _charge(charge)
                old_status = PixPaymentStatus(charge["status"])
                if old_status == PixPaymentStatus.SUCCEEDED and event.status not in {
                    old_status, PixPaymentStatus.REFUNDED,
                }:
                    raise InvalidFinancialOperationError
                row = await connection.fetchrow(
                    "UPDATE pix_charges SET status=$2,updated_at=now() WHERE id=$1 RETURNING *",
                    charge["id"], str(event.status),
                )
                assert row is not None
                if event.status == PixPaymentStatus.SUCCEEDED and old_status != event.status:
                    fee = (event.amount * platform_fee_rate).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    net = event.amount - fee
                    entries = (
                        (LedgerEntryKind.GROSS_CREDIT, event.amount, "Pagamento PIX aprovado"),
                        (LedgerEntryKind.PLATFORM_FEE, -fee, "Comissão da plataforma"),
                        (LedgerEntryKind.CREATOR_CREDIT, net, "Saldo disponível do criador"),
                    )
                    await connection.executemany(
                        "INSERT INTO financial_entries "
                        "(id,creator_id,charge_id,kind,amount,currency,description) "
                        "VALUES ($1,$2,$3,$4,$5,$6,$7)",
                        [(uuid4(), charge["creator_id"], charge["id"], str(kind), value,
                          event.currency, description) for kind, value, description in entries],
                    )
                    if charge["order_id"] is not None:
                        await connection.execute(
                            "UPDATE orders SET status='PAID' WHERE id=$1", charge["order_id"]
                        )
                        await connection.execute(
                            "INSERT INTO entitlements "
                            "(id,user_id,kind,resource_id,source_order_id) "
                            "SELECT $1,o.user_id,'STREAM',p.stream_id,o.id FROM orders o "
                            "JOIN products p ON p.id=o.product_id WHERE o.id=$2 "
                            "ON CONFLICT (user_id,kind,resource_id) "
                            "WHERE revoked_at IS NULL DO NOTHING",
                            uuid4(), charge["order_id"],
                        )
                elif (
                    event.status == PixPaymentStatus.REFUNDED
                    and old_status == PixPaymentStatus.SUCCEEDED
                ):
                    fee = (event.amount * platform_fee_rate).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    await connection.execute(
                        "INSERT INTO financial_entries "
                        "(id,creator_id,charge_id,kind,amount,currency,description) "
                        "VALUES ($1,$2,$3,'REFUND_DEBIT',$4,$5,'Pagamento reembolsado')",
                        uuid4(), charge["creator_id"], charge["id"], -(event.amount - fee),
                        event.currency,
                    )
                    if charge["order_id"] is not None:
                        await connection.execute(
                            "UPDATE orders SET status='REFUNDED' WHERE id=$1",
                            charge["order_id"],
                        )
                        await connection.execute(
                            "UPDATE entitlements SET revoked_at=now() "
                            "WHERE source_order_id=$1 AND revoked_at IS NULL",
                            charge["order_id"],
                        )
                return _charge(row)
        finally:
            await connection.close()

    async def balance(self, creator_id: UUID) -> CreatorBalance:
        connection = await self._connect()
        try:
            value = await connection.fetchval(
                "SELECT COALESCE(sum(amount),0) FROM financial_entries "
                "WHERE creator_id=$1 AND kind IN "
                "('CREATOR_CREDIT','WITHDRAWAL_DEBIT','REFUND_DEBIT')",
                creator_id,
            )
            return CreatorBalance(creator_id, value, "BRL")
        finally:
            await connection.close()

    async def history(self, creator_id: UUID) -> list[FinancialEntry]:
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                "SELECT * FROM financial_entries WHERE creator_id=$1 ORDER BY created_at DESC,id",
                creator_id,
            )
            return [_entry(row) for row in rows]
        finally:
            await connection.close()

    async def request_withdrawal(
        self, creator_id: UUID, amount: Decimal, destination_reference: str
    ) -> Withdrawal:
        connection = await self._connect()
        try:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext($1::text))", str(creator_id)
                )
                available = await connection.fetchval(
                    "SELECT COALESCE(sum(amount),0) FROM financial_entries "
                    "WHERE creator_id=$1 AND kind IN "
                    "('CREATOR_CREDIT','WITHDRAWAL_DEBIT','REFUND_DEBIT')", creator_id,
                )
                if available < amount:
                    raise InsufficientBalanceError
                withdrawal_id = uuid4()
                row = await connection.fetchrow(
                    "INSERT INTO withdrawals "
                    "(id,creator_id,amount,currency,destination_reference,status) "
                    "VALUES ($1,$2,$3,'BRL',$4,'REQUESTED') RETURNING *",
                    withdrawal_id, creator_id, amount, destination_reference,
                )
                await connection.execute(
                    "INSERT INTO financial_entries "
                    "(id,creator_id,withdrawal_id,kind,amount,currency,description) "
                    "VALUES ($1,$2,$3,'WITHDRAWAL_DEBIT',$4,'BRL','Saque solicitado')",
                    uuid4(), creator_id, withdrawal_id, -amount,
                )
                assert row is not None
                return _withdrawal(row)
        finally:
            await connection.close()

    async def list_withdrawals(self, creator_id: UUID) -> list[Withdrawal]:
        connection = await self._connect()
        try:
            rows = await connection.fetch(
                "SELECT * FROM withdrawals WHERE creator_id=$1 ORDER BY created_at DESC",
                creator_id,
            )
            return [_withdrawal(row) for row in rows]
        finally:
            await connection.close()
