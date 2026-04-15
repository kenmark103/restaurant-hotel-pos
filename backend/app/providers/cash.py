"""
providers/cash.py — Cash payment provider
─────────────────────────────────────────────────────────────────────────────
Synchronous: no network calls.  Records instantly as SUCCESS.
Used for cash, complimentary, and room-charge tender types.
"""

from app.providers.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderStatus,
)


class CashProvider(BasePaymentProvider):

    @property
    def name(self) -> str:
        return "cash"

    @property
    def supports_async_confirmation(self) -> bool:
        return False

    async def initiate(self, request: PaymentRequest) -> PaymentResult:
        return PaymentResult(
            status=ProviderStatus.SUCCESS,
            provider_reference=f"CASH-{request.reference}",
            provider_status="paid",
            instructions=None,
        )