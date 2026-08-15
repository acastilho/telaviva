from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

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
from app.finance.provider import FakePaymentProvider, ProviderCharge, ProviderWebhookEvent
from app.finance.repository import InsufficientBalanceError
from app.finance.routes import get_finance_repository, get_payment_provider
from app.identity.models import Role, User
from app.identity.routes import get_current_user
from app.main import app

creator = User(uuid4(), "creator@example.com", "hash", Role.CREATOR, datetime.now(UTC))
viewer = User(uuid4(), "viewer@example.com", "hash", Role.VIEWER, datetime.now(UTC))


class MemoryFinanceRepository:
    def __init__(self) -> None:
        self.charges: dict[UUID, PixCharge] = {}
        self.entries: list[FinancialEntry] = []
        self.withdrawals: list[Withdrawal] = []
        self.events: set[tuple[str, str]] = set()

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
        assert creator_id is not None and amount is not None
        now = datetime.now(UTC)
        charge = PixCharge(
            uuid4(), payer_id, creator_id, purpose, order_id, provider, f"pending-{uuid4()}",
            PixPaymentStatus.PENDING, amount, currency, None, None, now, now,
        )
        self.charges[charge.id] = charge
        return charge

    async def activate_charge(self, charge_id: UUID, result: ProviderCharge) -> PixCharge:
        old = self.charges[charge_id]
        charge = PixCharge(
            old.id, old.payer_id, old.creator_id, old.purpose, old.order_id, old.provider,
            result.reference, old.status, old.amount, old.currency, result.pix_copy_paste,
            result.expires_at, old.created_at, datetime.now(UTC),
        )
        self.charges[charge.id] = charge
        return charge

    async def get_charge(self, charge_id: UUID, payer_id: UUID) -> PixCharge:
        charge = self.charges[charge_id]
        assert charge.payer_id == payer_id
        return charge

    async def apply_webhook(
        self, provider: str, event: ProviderWebhookEvent, platform_fee_rate: Decimal
    ) -> PixCharge:
        charge = next(
            item
            for item in self.charges.values()
            if item.provider_reference == event.charge_reference
        )
        event_key = (provider, event.event_id)
        if event_key in self.events:
            return charge
        self.events.add(event_key)
        updated = PixCharge(
            charge.id, charge.payer_id, charge.creator_id, charge.purpose, charge.order_id,
            charge.provider, charge.provider_reference, event.status, charge.amount,
            charge.currency, charge.pix_copy_paste, charge.expires_at, charge.created_at,
            datetime.now(UTC),
        )
        self.charges[updated.id] = updated
        if event.status == PixPaymentStatus.SUCCEEDED:
            fee = (event.amount * platform_fee_rate).quantize(Decimal("0.01"))
            for kind, amount in (
                (LedgerEntryKind.GROSS_CREDIT, event.amount),
                (LedgerEntryKind.PLATFORM_FEE, -fee),
                (LedgerEntryKind.CREATOR_CREDIT, event.amount - fee),
            ):
                self.entries.append(FinancialEntry(
                    uuid4(), charge.creator_id, charge.id, None, kind, amount, "BRL",
                    kind.value, datetime.now(UTC),
                ))
        return updated

    async def balance(self, creator_id: UUID) -> CreatorBalance:
        included = {
            LedgerEntryKind.CREATOR_CREDIT,
            LedgerEntryKind.WITHDRAWAL_DEBIT,
            LedgerEntryKind.REFUND_DEBIT,
        }
        total = sum(
            (
                entry.amount
                for entry in self.entries
                if entry.creator_id == creator_id and entry.kind in included
            ),
            Decimal(),
        )
        return CreatorBalance(creator_id, total, "BRL")

    async def history(self, creator_id: UUID) -> list[FinancialEntry]:
        return [entry for entry in reversed(self.entries) if entry.creator_id == creator_id]

    async def request_withdrawal(
        self, creator_id: UUID, amount: Decimal, destination_reference: str
    ) -> Withdrawal:
        if (await self.balance(creator_id)).available < amount:
            raise InsufficientBalanceError
        now = datetime.now(UTC)
        withdrawal = Withdrawal(
            uuid4(), creator_id, amount, "BRL", destination_reference,
            WithdrawalStatus.REQUESTED, None, now, now,
        )
        self.withdrawals.append(withdrawal)
        self.entries.append(FinancialEntry(
            uuid4(), creator_id, None, withdrawal.id, LedgerEntryKind.WITHDRAWAL_DEBIT,
            -amount, "BRL", "Saque solicitado", now,
        ))
        return withdrawal

    async def list_withdrawals(self, creator_id: UUID) -> list[Withdrawal]:
        return [item for item in self.withdrawals if item.creator_id == creator_id]


repository = MemoryFinanceRepository()
current_user = viewer
client = TestClient(app)


def setup_function() -> None:
    global repository, current_user
    repository = MemoryFinanceRepository()
    current_user = viewer
    app.dependency_overrides[get_finance_repository] = lambda: repository
    app.dependency_overrides[get_payment_provider] = FakePaymentProvider
    app.dependency_overrides[get_current_user] = lambda: current_user


def teardown_function() -> None:
    app.dependency_overrides.clear()


def create_tip() -> dict[str, object]:
    response = client.post("/pix/charges", json={
        "purpose": "TIP", "creator_id": str(creator.id), "amount": "25.00",
    })
    assert response.status_code == 201
    return response.json()


def approve(charge: dict[str, object], event_id: str = "evt-1") -> None:
    response = client.post(
        "/pix/webhooks/fake",
        headers={"x-fake-signature": "development-webhook"},
        json={
            "event_id": event_id, "charge_reference": charge["provider_reference"],
            "status": "SUCCEEDED", "amount": "25.00", "currency": "BRL",
        },
    )
    assert response.status_code == 200


def test_tip_webhook_is_idempotent_and_credits_net_creator_balance() -> None:
    global current_user
    charge = create_tip()
    assert charge["status"] == "PENDING"
    assert str(charge["pix_copy_paste"]).startswith("000201-TELAVIVA-")
    approve(charge)
    approve(charge)
    status_response = client.get(f"/pix/charges/{charge['id']}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "SUCCEEDED"
    current_user = creator
    balance = client.get("/finance/balance")
    assert balance.status_code == 200
    assert balance.json()["available"] == "22.50"
    history = client.get("/finance/history").json()
    assert [entry["kind"] for entry in history] == [
        "CREATOR_CREDIT", "PLATFORM_FEE", "GROSS_CREDIT",
    ]


def test_withdrawal_reserves_balance_and_only_accepts_opaque_destination() -> None:
    global current_user
    charge = create_tip()
    approve(charge)
    current_user = creator
    assert client.post("/finance/withdrawals", json={
        "amount": "10.00", "destination_reference": "person@example.com",
    }).status_code == 422
    withdrawal = client.post("/finance/withdrawals", json={
        "amount": "10.00", "destination_reference": "dest_provider_token_123",
    })
    assert withdrawal.status_code == 201
    assert withdrawal.json()["status"] == "REQUESTED"
    assert client.get("/finance/balance").json()["available"] == "12.50"
    assert client.post("/finance/withdrawals", json={
        "amount": "20.00", "destination_reference": "dest_provider_token_123",
    }).status_code == 409


def test_webhook_signature_and_finance_authorization_are_enforced() -> None:
    charge = create_tip()
    assert client.post("/pix/webhooks/fake", json={
        "event_id": "evt", "charge_reference": charge["provider_reference"],
        "status": "SUCCEEDED", "amount": "25.00",
    }).status_code == 401
    assert client.get("/finance/balance").status_code == 403


def test_tip_and_class_purchase_payloads_are_distinct() -> None:
    assert client.post("/pix/charges", json={
        "purpose": "TIP", "creator_id": str(creator.id), "order_id": str(uuid4()),
        "amount": "5.00",
    }).status_code == 422
    assert client.post("/pix/charges", json={
        "purpose": "CLASS_PURCHASE", "creator_id": str(creator.id), "amount": "5.00",
    }).status_code == 422
