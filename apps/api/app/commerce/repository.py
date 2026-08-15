from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from app.commerce.models import (
    AccessDecision,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    ProductKind,
)
from app.config import Settings


class ProductNotFoundError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class InvalidPaymentError(Exception):
    pass


class StreamNotOwnedError(Exception):
    pass


class CommerceRepository(Protocol):
    async def create_product(self, creator_id: UUID, **values: object) -> Product: ...
    async def create_order(self, user_id: UUID, product_id: UUID) -> Order: ...
    async def record_payment(self, **values: object) -> Payment: ...
    async def invite(self, stream_id: UUID, creator_id: UUID, user_id: UUID) -> None: ...
    async def check_access(self, stream_id: UUID, user_id: UUID) -> AccessDecision: ...


def _product(row: asyncpg.Record) -> Product:
    return Product(
        row["id"], row["creator_id"], ProductKind(row["kind"]), row["stream_id"],
        row["name"], row["price"], row["currency"], row["subscription_days"],
        row["active"], row["created_at"],
    )


def _order(row: asyncpg.Record) -> Order:
    return Order(
        row["id"], row["user_id"], row["product_id"], row["amount"], row["currency"],
        OrderStatus(row["status"]), row["created_at"],
    )


def _payment(row: asyncpg.Record) -> Payment:
    return Payment(
        row["id"], row["order_id"], row["provider"], row["provider_reference"],
        PaymentStatus(row["status"]), row["amount"], row["currency"], row["created_at"],
    )


class PostgresCommerceRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._url)

    async def create_product(self, creator_id: UUID, **values: object) -> Product:
        connection = await self._connect()
        try:
            stream_id = values["stream_id"]
            kind = values["kind"]
            if (kind == ProductKind.CLASS) != (stream_id is not None):
                raise StreamNotOwnedError
            if stream_id is not None:
                stream = await connection.fetchrow(
                    "SELECT access_type,price FROM scheduled_streams "
                    "WHERE id=$1 AND creator_id=$2", stream_id, creator_id,
                )
                if (
                    stream is None or stream["access_type"] != "PAID"
                    or stream["price"] != values["price"]
                ):
                    raise StreamNotOwnedError
            row = await connection.fetchrow(
                "INSERT INTO products (id,creator_id,kind,stream_id,name,price,currency,subscription_days) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING *",
                uuid4(), creator_id, str(kind), stream_id, values["name"], values["price"],
                values["currency"], values["subscription_days"],
            )
            assert row is not None
            return _product(row)
        finally:
            await connection.close()

    async def create_order(self, user_id: UUID, product_id: UUID) -> Order:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "INSERT INTO orders (id,user_id,product_id,amount,currency) "
                "SELECT $1,$2,id,price,currency FROM products WHERE id=$3 AND active "
                "RETURNING *", uuid4(), user_id, product_id,
            )
            if row is None:
                raise ProductNotFoundError
            return _order(row)
        finally:
            await connection.close()

    async def record_payment(self, **values: object) -> Payment:
        connection = await self._connect()
        try:
            async with connection.transaction():
                order = await connection.fetchrow(
                    "SELECT o.*,p.kind,p.stream_id,p.creator_id,p.subscription_days FROM orders o "
                    "JOIN products p ON p.id=o.product_id WHERE o.id=$1 FOR UPDATE",
                    values["order_id"],
                )
                if order is None:
                    raise OrderNotFoundError
                if order["amount"] != values["amount"] or order["currency"] != values["currency"]:
                    raise InvalidPaymentError
                row = await connection.fetchrow(
                    "INSERT INTO payments (id,order_id,provider,provider_reference,status,amount,currency) "
                    "VALUES ($1,$2,$3,$4,$5,$6,$7) "
                    "ON CONFLICT (provider,provider_reference) DO UPDATE SET status=CASE "
                    "WHEN payments.status='SUCCEEDED' AND EXCLUDED.status='FAILED' "
                    "THEN payments.status ELSE EXCLUDED.status END "
                    "WHERE payments.order_id=EXCLUDED.order_id "
                    "AND payments.amount=EXCLUDED.amount AND payments.currency=EXCLUDED.currency "
                    "RETURNING *", uuid4(), values["order_id"], values["provider"],
                    values["provider_reference"], str(values["status"]), values["amount"],
                    values["currency"],
                )
                if row is None:
                    raise InvalidPaymentError
                if values["status"] == PaymentStatus.SUCCEEDED:
                    await connection.execute("UPDATE orders SET status='PAID' WHERE id=$1", order["id"])
                    entitlement_kind = "STREAM" if order["kind"] == "CLASS" else "CREATOR_SUBSCRIPTION"
                    resource_id = order["stream_id"] or order["creator_id"]
                    await connection.execute(
                        "INSERT INTO entitlements (id,user_id,kind,resource_id,source_order_id,expires_at) "
                        "VALUES ($1,$2,$3,$4,$5,CASE WHEN $6::integer IS NULL THEN NULL "
                        "ELSE now()+make_interval(days => $6) END) "
                        "ON CONFLICT (user_id,kind,resource_id) "
                        "WHERE revoked_at IS NULL DO NOTHING",
                        uuid4(), order["user_id"], entitlement_kind, resource_id, order["id"],
                        order["subscription_days"],
                    )
                elif values["status"] == PaymentStatus.REFUNDED:
                    await connection.execute("UPDATE orders SET status='REFUNDED' WHERE id=$1", order["id"])
                    await connection.execute(
                        "UPDATE entitlements SET revoked_at=now() WHERE source_order_id=$1 AND revoked_at IS NULL",
                        order["id"],
                    )
                return _payment(row)
        finally:
            await connection.close()

    async def invite(self, stream_id: UUID, creator_id: UUID, user_id: UUID) -> None:
        connection = await self._connect()
        try:
            result = await connection.execute(
                "INSERT INTO stream_invites (stream_id,user_id,invited_by) "
                "SELECT id,$3,$2 FROM scheduled_streams WHERE id=$1 AND creator_id=$2 "
                "ON CONFLICT DO NOTHING", stream_id, creator_id, user_id,
            )
            if result == "INSERT 0 0" and not await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM scheduled_streams WHERE id=$1 AND creator_id=$2)",
                stream_id, creator_id,
            ):
                raise StreamNotOwnedError
        finally:
            await connection.close()

    async def check_access(self, stream_id: UUID, user_id: UUID) -> AccessDecision:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(
                "SELECT s.creator_id,s.access_type,"
                "(SELECT e.id FROM entitlements e WHERE e.user_id=$2 AND e.revoked_at IS NULL "
                "AND e.starts_at<=now() AND (e.expires_at IS NULL OR e.expires_at>now()) AND "
                "((s.access_type='PAID' AND e.kind='STREAM' AND e.resource_id=s.id) OR "
                "(s.access_type='SUBSCRIBERS' AND e.kind='CREATOR_SUBSCRIPTION' "
                "AND e.resource_id=s.creator_id))) "
                "ORDER BY e.expires_at DESC NULLS FIRST LIMIT 1) entitlement_id,"
                "EXISTS(SELECT 1 FROM stream_invites i WHERE i.stream_id=s.id AND i.user_id=$2) invited "
                "FROM scheduled_streams s WHERE s.id=$1", stream_id, user_id,
            )
            if row is None:
                raise ProductNotFoundError
            access_type = row["access_type"]
            entitlement_id = row["entitlement_id"]
            granted = (
                row["creator_id"] == user_id or access_type == "FREE"
                or (access_type == "PRIVATE" and row["invited"])
                or (access_type == "PAID" and entitlement_id is not None)
                or (access_type == "SUBSCRIBERS" and entitlement_id is not None)
            )
            reason = "OWNER" if row["creator_id"] == user_id else (
                "FREE" if access_type == "FREE" else "ENTITLED" if entitlement_id else
                "INVITED" if row["invited"] else "ENTITLEMENT_REQUIRED"
            )
            decision = AccessDecision(
                stream_id, user_id, granted, reason, entitlement_id, datetime.now(UTC)
            )
            await connection.execute(
                "INSERT INTO stream_accesses (id,stream_id,user_id,granted,reason,entitlement_id) "
                "VALUES ($1,$2,$3,$4,$5,$6)", uuid4(), stream_id, user_id, granted, reason,
                entitlement_id,
            )
            return decision
        finally:
            await connection.close()
