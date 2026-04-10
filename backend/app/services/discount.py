"""
app/services/discount.py  — new file.
Handles applying and removing discounts on orders.
Called from order endpoints — keeps order.py focused on order state.
"""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import DiscountType, PosOrderStatus
from app.models.order_discount import OrderDiscount
from app.models.pos_order import PosOrder
from app.models.pos_order_item import PosOrderItem
from app.schemas.order import DiscountApply

MONEY_QUANT = Decimal("0.01")


class DiscountError(Exception):
    pass


def _money(v: Decimal) -> Decimal:
    return v.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


async def _load_order(db: AsyncSession, order_id: int) -> PosOrder:
    result = await db.execute(
        select(PosOrder)
        .options(
            selectinload(PosOrder.items),
            selectinload(PosOrder.discounts),
        )
        .where(PosOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise DiscountError("Order not found.")
    if order.status not in [PosOrderStatus.OPEN, PosOrderStatus.SENT]:
        raise DiscountError("Cannot modify discounts on a closed or voided order.")
    return order


def _compute_discount_amount(
    discount_type: DiscountType,
    value: Decimal,
    base_amount: Decimal,
) -> Decimal:
    if discount_type == DiscountType.PERCENT:
        if value > Decimal("100"):
            raise DiscountError("Percentage discount cannot exceed 100%.")
        return _money(base_amount * value / Decimal("100"))
    else:
        if value > base_amount:
            raise DiscountError("Fixed discount cannot exceed the amount being discounted.")
        return _money(value)


async def _recompute_discount_total(db: AsyncSession, order: PosOrder) -> None:
    """Sum all active discount amounts and write to order.discount_total."""
    total = sum(
        (d.amount for d in order.discounts),
        Decimal("0.00"),
    )
    order.discount_total = _money(total)
    # Adjust total_amount to reflect discount
    # total_amount = subtotal + tax - discounts (floored at 0)
    order.total_amount = _money(max(
        order.subtotal + order.tax_amount - order.discount_total,
        Decimal("0.00"),
    ))


async def apply_discount(
    db: AsyncSession,
    order_id: int,
    payload: DiscountApply,
    authorized_by_user_id: int,
) -> PosOrder:
    order = await _load_order(db, order_id)

    if payload.order_item_id is not None:
        # line-level discount
        item = next(
            (i for i in order.items if i.id == payload.order_item_id and not i.is_voided),
            None,
        )
        if item is None:
            raise DiscountError("Order item not found or is voided.")
        base_amount = item.line_total
    else:
        # order-level discount
        base_amount = order.subtotal

    amount = _compute_discount_amount(payload.discount_type, payload.value, base_amount)

    discount = OrderDiscount(
        order_id=order.id,
        order_item_id=payload.order_item_id,
        discount_type=payload.discount_type,
        value=payload.value,
        amount=amount,
        reason=payload.reason,
        authorized_by_user_id=authorized_by_user_id,
    )
    db.add(discount)
    await db.flush()

    # reload discounts to include the new one
    order = await _load_order(db, order_id)
    await _recompute_discount_total(db, order)
    await db.commit()
    return await _load_order(db, order_id)


async def remove_discount(
    db: AsyncSession,
    order_id: int,
    discount_id: int,
) -> PosOrder:
    order = await _load_order(db, order_id)

    discount = next((d for d in order.discounts if d.id == discount_id), None)
    if discount is None:
        raise DiscountError("Discount not found on this order.")

    await db.delete(discount)
    await db.flush()

    order = await _load_order(db, order_id)
    await _recompute_discount_total(db, order)
    await db.commit()
    return await _load_order(db, order_id)