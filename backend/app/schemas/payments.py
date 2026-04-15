"""
schemas/payments.py — Payment domain schemas
─────────────────────────────────────────────────────────────────────────────
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import PaymentMethod
from app.providers.base import ProviderStatus


class InitiatePaymentRequest(BaseModel):
    order_id: int
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    reference: Optional[str] = None
    record_only: bool = True        # MVP default — skip gateway


class VerifyPaymentRequest(BaseModel):
    method: PaymentMethod
    provider_reference: str


class PaymentResultResponse(BaseModel):
    status: ProviderStatus
    provider_reference: Optional[str] = None
    checkout_url: Optional[str] = None      # PesaPal redirect
    instructions: Optional[str] = None     # M-Pesa: "Check your phone"
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}