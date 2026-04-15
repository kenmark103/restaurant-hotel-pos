"""
schemas/orders.py — Order request / response schemas
─────────────────────────────────────────────────────────────────────────────
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import DiscountType, OrderType, PaymentMethod, PosOrderStatus


# ── Request schemas ─────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    order_type: OrderType
    branch_id: Optional[int] = None       # required for non-dine-in
    table_id: Optional[int] = None        # required for dine-in
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    room_number: Optional[str] = None
    note: Optional[str] = None


class AddOrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)
    variant_id: Optional[int] = None
    modifier_option_ids: Optional[list[int]] = None
    note: Optional[str] = Field(default=None, max_length=500)


class UpdateQuantityRequest(BaseModel):
    quantity: int = Field(ge=1)


class VoidItemRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class VoidOrderRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class SplitPaymentEntry(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    reference: Optional[str] = None


class CloseOrderRequest(BaseModel):
    """Supports single-tender and split-tender."""
    payment_method: PaymentMethod
    amount_paid: Decimal = Field(gt=0)
    split_payments: Optional[list[SplitPaymentEntry]] = None


class ApplyDiscountRequest(BaseModel):
    discount_type: DiscountType
    value: Decimal = Field(gt=0)
    order_item_id: Optional[int] = None
    reason: Optional[str] = None


class SendToKitchenRequest(BaseModel):
    station_filter: Optional[str] = None  # e.g. "bar" — send only to that station


# ── Response schemas ─────────────────────────────────────────────────────────

class ModifierRead(BaseModel):
    option_name: str
    price_delta: Decimal
    model_config = {"from_attributes": True}


class OrderItemRead(BaseModel):
    id: int
    menu_item_name: str
    variant_name: Optional[str]
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    note: Optional[str]
    is_voided: bool
    void_reason: Optional[str]
    sent_to_kitchen: bool
    modifiers: list[ModifierRead] = []
    model_config = {"from_attributes": True}


class PaymentRead(BaseModel):
    id: int
    method: PaymentMethod
    amount: Decimal
    reference: Optional[str]
    model_config = {"from_attributes": True}


class TableRead(BaseModel):
    id: int
    table_number: str
    floor_zone: Optional[str]
    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: int
    branch_id: int
    order_type: OrderType
    status: PosOrderStatus
    table: Optional[TableRead]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    room_number: Optional[str]
    note: Optional[str]
    subtotal: Decimal
    tax_amount: Decimal
    discount_total: Decimal
    total_amount: Decimal
    amount_paid: Optional[Decimal]
    change_due: Optional[Decimal]
    payment_method: Optional[PaymentMethod]
    items: list[OrderItemRead] = []
    payments: list[PaymentRead] = []
    model_config = {"from_attributes": True}