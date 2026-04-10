from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DiscountType, OrderType, PaymentMethod, PosOrderStatus


class PosOrderCreate(BaseModel):
    order_type: OrderType = OrderType.DINE_IN
    table_id: int | None = None
    branch_id: int | None = None
    room_number: str | None = Field(default=None, max_length=20)
    customer_name: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)


class PosOrderItemAdd(BaseModel):
    menu_item_id: int
    variant_id: int | None = None
    quantity: int = Field(default=1, ge=1)
    note: str | None = Field(default=None, max_length=500)


class PosOrderItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)
    note: str | None = Field(default=None, max_length=500)


class PosOrderItemVoid(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class DiscountApply(BaseModel):
    discount_type: DiscountType
    value: Decimal = Field(..., gt=0)
    order_item_id: int | None = None
    reason: str | None = Field(default=None, max_length=255)


class DiscountRead(BaseModel):
    id: int
    order_id: int
    order_item_id: int | None
    discount_type: DiscountType
    value: Decimal
    amount: Decimal
    reason: str | None

    model_config = ConfigDict(from_attributes=True)


class PosOrderClose(BaseModel):
    payment_method: PaymentMethod
    amount_paid: Decimal = Field(..., ge=0)


class PosOrderItemRead(BaseModel):
    id: int
    order_id: int
    menu_item_id: int
    menu_item_name: str
    variant_id: int | None
    variant_name: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    note: str | None
    is_voided: bool
    void_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PosOrderRead(BaseModel):
    id: int
    branch_id: int
    table_id: int | None
    staff_user_id: int
    order_type: OrderType
    status: PosOrderStatus
    room_number: str | None
    customer_name: str | None
    note: str | None
    subtotal: Decimal
    tax_amount: Decimal
    discount_total: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod | None
    amount_paid: Decimal | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[PosOrderItemRead] = Field(default_factory=list)
    discounts: list[DiscountRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
