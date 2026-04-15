"""
payment_service.py — Payment domain service
─────────────────────────────────────────────────────────────────────────────
Responsibilities:
  • Provider selection by payment method
  • Initiate / verify / refund flow
  • Write PosPayment rows (the authoritative record)
  • Route inbound webhooks to the correct provider
  • Publish PaymentRecorded events

MVP mode (blueprint §7.1):
  Call with record_only=True to skip the gateway entirely and just write the
  PosPayment row.  This is the default until real gateways are tested.

Provider registration:
  Providers are registered at startup in app/core/listeners.py via
  payment_service.register_provider(method, provider_instance).
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus, PaymentRecorded
from app.db.models import (
    AuditAction,
    AuditLog,
    Branch,
    PaymentMethod,
    PosOrder,
    PosOrderStatus,
    PosPayment,
    PrintJobStatus,
    PrintJobType,
)
from app.services.base import NotFoundError, ValidationError, to_money
from app.providers.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderStatus,
)
from app.providers.cash import CashProvider


class PaymentService:
    """
    Orchestrates payment initiation, confirmation, and recording.

    Inject via FastAPI dependency — do NOT construct manually in routes.
    """

    def __init__(
        self,
        db: AsyncSession,
        current_user=None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.db = db
        self.user = current_user
        self.bus = event_bus
        # Provider registry: PaymentMethod → BasePaymentProvider
        self._providers: dict[PaymentMethod, BasePaymentProvider] = {
            PaymentMethod.CASH: CashProvider(),
            PaymentMethod.COMPLIMENTARY: CashProvider(),  # same no-op flow
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Provider registry
    # ─────────────────────────────────────────────────────────────────────────

    def register_provider(
        self, method: PaymentMethod, provider: BasePaymentProvider
    ) -> None:
        """Register a gateway provider for a payment method at startup."""
        self._providers[method] = provider

    def get_provider(self, method: PaymentMethod) -> BasePaymentProvider:
        provider = self._providers.get(method)
        if not provider:
            raise ValidationError(
                f"No payment provider registered for method '{method}'. "
                "Check startup configuration."
            )
        return provider

    # ─────────────────────────────────────────────────────────────────────────
    # Initiate payment
    # ─────────────────────────────────────────────────────────────────────────

    async def initiate_payment(
        self,
        order_id: int,
        method: PaymentMethod,
        amount: Decimal,
        reference: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        record_only: bool = True,   # MVP default: skip gateway, just record
    ) -> PaymentResult:
        """
        Initiate a payment for an order.

        In record_only mode (MVP): creates PosPayment row immediately and
        returns SUCCESS without calling any external gateway.

        In live mode: calls the provider, creates PosPayment on SUCCESS or
        AWAITING_CONFIRMATION (the row is created with a pending state that
        is confirmed by the webhook).
        """
        order = await self.db.get(PosOrder, order_id)
        if not order:
            raise NotFoundError("PosOrder")
        if order.status == PosOrderStatus.CLOSED:
            raise ValidationError("Order is already closed")
        if order.status == PosOrderStatus.VOIDED:
            raise ValidationError("Cannot pay a voided order")

        amount = to_money(amount)
        branch = await self.db.get(Branch, order.branch_id)
        branch_code = branch.code if branch else "POS"
        ref = reference or f"{branch_code}-{order_id:05d}-{int(datetime.now(UTC).timestamp())}"

        if record_only:
            return await self._record_payment(
                order_id=order_id,
                method=method,
                amount=amount,
                reference=ref,
                branch_id=order.branch_id,
            )

        provider = self.get_provider(method)
        req = PaymentRequest(
            order_id=order_id,
            amount=amount,
            currency=(await self._get_currency(order.branch_id)),
            reference=ref,
            customer_phone=customer_phone or order.customer_phone,
            customer_email=customer_email,
            description=f"Order {ref}",
        )
        result = await provider.initiate(req)

        if result.status in (ProviderStatus.SUCCESS, ProviderStatus.AWAITING_CONFIRMATION):
            await self._record_payment(
                order_id=order_id,
                method=method,
                amount=amount,
                reference=result.provider_reference or ref,
                branch_id=order.branch_id,
            )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Verify pending payment
    # ─────────────────────────────────────────────────────────────────────────

    async def verify_payment(
        self,
        method: PaymentMethod,
        provider_reference: str,
    ) -> PaymentResult:
        """Poll a gateway for the status of a pending payment."""
        provider = self.get_provider(method)
        return await provider.verify(provider_reference)

    # ─────────────────────────────────────────────────────────────────────────
    # Webhook dispatcher (called by route handlers)
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_webhook(
        self,
        method: PaymentMethod,
        payload: dict,
        order_id: Optional[int] = None,
    ) -> PaymentResult:
        """
        Route an inbound IPN/callback to the correct provider.
        On SUCCESS, updates the PosPayment reference.
        """
        provider = self.get_provider(method)
        result = await provider.handle_webhook(payload)

        if result.status == ProviderStatus.SUCCESS and order_id and result.provider_reference:
            # Update reference on the PosPayment row
            payment = await self.db.scalar(
                select(PosPayment).where(PosPayment.order_id == order_id)
            )
            if payment:
                payment.reference = result.provider_reference
                await self.db.commit()

            if self.bus:
                order = await self.db.get(PosOrder, order_id)
                if order:
                    await self.bus.publish(
                        PaymentRecorded(
                            order_id=order_id,
                            branch_id=order.branch_id,
                            method=method.value,
                            amount=Decimal(str(payment.amount)) if payment else Decimal("0"),
                            reference=result.provider_reference,
                        )
                    )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _record_payment(
        self,
        order_id: int,
        method: PaymentMethod,
        amount: Decimal,
        reference: str,
        branch_id: int,
    ) -> PaymentResult:
        """Write a PosPayment row and publish the PaymentRecorded event."""
        payment = PosPayment(
            order_id=order_id,
            method=method,
            amount=amount,
            reference=reference,
        )
        self.db.add(payment)

        if self.user:
            self.db.add(
                AuditLog(
                    branch_id=branch_id,
                    actor_id=self.user.id,
                    action=AuditAction.DISCOUNT_APPLIED,  # reuse nearest existing; add PAYMENT_RECORDED if desired
                    entity_type="pos_payment",
                    payload={"method": method, "amount": str(amount), "ref": reference},
                )
            )

        await self.db.commit()
        await self.db.refresh(payment)

        if self.bus:
            await self.bus.publish(
                PaymentRecorded(
                    order_id=order_id,
                    branch_id=branch_id,
                    method=method.value,
                    amount=amount,
                    reference=reference,
                )
            )

        return PaymentResult(
            status=ProviderStatus.SUCCESS,
            provider_reference=reference,
        )

    async def _get_currency(self, branch_id: int) -> str:
        from app.db.models import BranchSettings, VenueSettings
        from sqlalchemy import select as sel

        branch_settings = await self.db.scalar(
            sel(BranchSettings).where(BranchSettings.branch_id == branch_id)
        )
        venue = await self.db.scalar(sel(VenueSettings))
        return (venue.currency if venue else None) or "KES"

    async def list_payments(self, order_id: int) -> list[PosPayment]:
        result = await self.db.execute(
            select(PosPayment).where(PosPayment.order_id == order_id)
        )
        return list(result.scalars().all())