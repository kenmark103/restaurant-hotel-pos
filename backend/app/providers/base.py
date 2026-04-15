"""
providers/base.py — Abstract payment provider interface
─────────────────────────────────────────────────────────────────────────────
Every payment gateway (M-Pesa, PesaPal, Stripe, cash) implements this
interface.  PaymentService uses only this contract — swapping providers
requires only injecting a different implementation.

Payment flow (blueprint §7.1 / §7.2):
  MVP   → record_only=True  — just write PosPayment rows, no gateway call
  Later → call initiate() / verify() against real gateway APIs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional


class ProviderStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # STK push, mobile redirect


@dataclass
class PaymentRequest:
    """Normalised input for any payment provider."""

    order_id: int
    amount: Decimal
    currency: str                   # ISO-4217, e.g. "KES"
    reference: str                  # Internal reference (order number / receipt no.)
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    description: str = "POS Payment"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Normalised result from a payment provider."""

    status: ProviderStatus
    provider_reference: Optional[str] = None   # Gateway's transaction ID
    provider_status: Optional[str] = None       # Raw status from gateway
    checkout_url: Optional[str] = None          # For redirect-based flows
    instructions: Optional[str] = None          # e.g. "Check your phone for prompt"
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None         # Full gateway response (for audit)


class BasePaymentProvider(ABC):
    """
    Contract that every payment provider must satisfy.

    Concrete implementations live in this package:
      • CashProvider    — no-op, just returns SUCCESS instantly
      • MpesaProvider   — Safaricom Daraja API (STK Push)
      • PesaPalProvider — PesaPal IPN-based flow
      • StripeProvider  — Stripe Payment Intents (card / international)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used in logs and DB records: 'mpesa', 'cash', etc."""
        ...

    @property
    def supports_async_confirmation(self) -> bool:
        """
        Return True if payment confirmation arrives asynchronously
        (STK push, IPN callback).  False for synchronous providers (cash, card terminal).
        """
        return False

    @abstractmethod
    async def initiate(self, request: PaymentRequest) -> PaymentResult:
        """
        Start the payment.  For synchronous providers (cash) this also
        completes it.  For async providers (M-Pesa STK), this triggers the
        user-facing prompt and returns AWAITING_CONFIRMATION.
        """
        ...

    async def verify(self, provider_reference: str) -> PaymentResult:
        """
        Poll or verify a pending payment by provider reference.
        Async providers must implement this.  Synchronous ones don't need to.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not support async verification."
        )

    async def handle_webhook(self, payload: dict) -> PaymentResult:
        """
        Process an inbound webhook / IPN callback from the gateway.
        Async providers (M-Pesa, PesaPal) must implement this.
        """
        raise NotImplementedError(
            f"Provider '{self.name}' does not handle webhooks."
        )

    def build_reference(self, order_id: int, branch_code: str) -> str:
        """Default reference format: BRANCH-ORDERID (e.g. NRB-00123)."""
        return f"{branch_code.upper()}-{order_id:05d}"