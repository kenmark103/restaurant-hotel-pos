from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.branch import Branch
from app.models.enums import OrderType, PosOrderStatus, TableStatus
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.pos_order import PosOrder
from app.models.pos_order_item import PosOrderItem
from app.models.pos_payment import PosPayment
from app.models.table import Table
from app.models.tax_config import TaxConfig
from app.schemas.order import PosOrderClose, PosOrderCreate, PosOrderItemAdd, PosOrderItemUpdate, PosOrderItemVoid

MONEY_QUANT = Decimal("0.01")


class OrderServiceError(Exception):
    pass


class OrderNotFoundError(OrderServiceError):
    pass


class OrderValidationError(OrderServiceError):
    pass


def _to_money(value: Decimal | int | float) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _order_query():
    return select(PosOrder).options(selectinload(PosOrder.items), selectinload(PosOrder.discounts))


async def _resolve_tax_config(db: AsyncSession, branch_id: int) -> TaxConfig | None:
    branch_result = await db.execute(
        select(TaxConfig).where(TaxConfig.branch_id == branch_id).order_by(TaxConfig.updated_at.desc())
    )
    branch_tax = branch_result.scalars().first()
    if branch_tax is not None:
        return branch_tax

    global_result = await db.execute(
        select(TaxConfig).where(TaxConfig.branch_id.is_(None)).order_by(TaxConfig.updated_at.desc())
    )
    return global_result.scalars().first()


async def _recompute_order_totals(db: AsyncSession, order: PosOrder) -> None:
    active_items = [item for item in order.items if not item.is_voided]
    subtotal = sum((item.line_total for item in active_items), Decimal("0.00"))
    order.subtotal = _to_money(subtotal)

    tax_amount = Decimal("0.00")
    tax_config = await _resolve_tax_config(db, order.branch_id)

    if tax_config is not None:
        rate = Decimal(str(tax_config.rate))
        if rate < Decimal("0.00"):
            rate = Decimal("0.00")

        if tax_config.is_inclusive:
            if rate > Decimal("0.00"):
                denominator = Decimal("1.00") + rate
                pre_tax_subtotal = order.subtotal / denominator
                tax_amount = order.subtotal - pre_tax_subtotal
        else:
            tax_amount = order.subtotal * rate

    order.tax_amount = _to_money(tax_amount)

    discount_total = _to_money(order.discount_total or Decimal("0.00"))
    if discount_total < Decimal("0.00"):
        discount_total = Decimal("0.00")
    order.discount_total = discount_total

    gross_total = order.subtotal + order.tax_amount
    order.total_amount = _to_money(max(gross_total - discount_total, Decimal("0.00")))


async def get_order(db: AsyncSession, order_id: int) -> PosOrder:
    result = await db.execute(_order_query().where(PosOrder.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise OrderNotFoundError("Order not found.")
    return order


async def list_orders(
    db: AsyncSession,
    branch_id: int | None = None,
    status: PosOrderStatus | None = None,
    active_only: bool = True,
) -> list[PosOrder]:
    statement = _order_query().order_by(PosOrder.created_at.desc())
    if branch_id is not None:
        statement = statement.where(PosOrder.branch_id == branch_id)
    if active_only:
        statement = statement.where(PosOrder.status.in_([PosOrderStatus.OPEN, PosOrderStatus.SENT]))
    elif status is not None:
        statement = statement.where(PosOrder.status == status)
    result = await db.execute(statement)
    return list(result.scalars().unique().all())


async def create_order(db: AsyncSession, payload: PosOrderCreate, staff_user_id: int) -> PosOrder:
    if payload.order_type == OrderType.DINE_IN:
        if payload.table_id is None:
            raise OrderValidationError("table_id is required for dine-in orders.")

        table_result = await db.execute(select(Table).where(Table.id == payload.table_id))
        table = table_result.scalar_one_or_none()
        if table is None:
            raise OrderNotFoundError("Table not found.")
        if table.status == TableStatus.CLEANING:
            raise OrderValidationError("Table is currently being cleaned.")

        existing_result = await db.execute(
            _order_query()
            .where(
                PosOrder.table_id == payload.table_id,
                PosOrder.status.in_([PosOrderStatus.OPEN, PosOrderStatus.SENT]),
            )
            .order_by(PosOrder.created_at.desc())
        )
        existing_order = existing_result.scalar_one_or_none()
        if existing_order is not None:
            if table.status != TableStatus.OCCUPIED:
                table.status = TableStatus.OCCUPIED
                await db.commit()
            return await get_order(db, existing_order.id)

        order = PosOrder(
            branch_id=table.branch_id,
            table_id=table.id,
            staff_user_id=staff_user_id,
            order_type=payload.order_type,
            status=PosOrderStatus.OPEN,
            room_number=payload.room_number,
            customer_name=payload.customer_name,
            note=payload.note,
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            discount_total=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )
        table.status = TableStatus.OCCUPIED
    else:
        if payload.table_id is not None:
            raise OrderValidationError("table_id is only allowed for dine-in orders.")
        if payload.branch_id is None:
            raise OrderValidationError("branch_id is required for non-dine-in orders.")

        branch_result = await db.execute(select(Branch).where(Branch.id == payload.branch_id))
        branch = branch_result.scalar_one_or_none()
        if branch is None:
            raise OrderNotFoundError("Branch not found.")

        order = PosOrder(
            branch_id=branch.id,
            table_id=None,
            staff_user_id=staff_user_id,
            order_type=payload.order_type,
            status=PosOrderStatus.OPEN,
            room_number=payload.room_number,
            customer_name=payload.customer_name,
            note=payload.note,
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            discount_total=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )

    db.add(order)
    await db.commit()
    return await get_order(db, order.id)


async def add_order_item(db: AsyncSession, order_id: int, payload: PosOrderItemAdd) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status != PosOrderStatus.OPEN:
        raise OrderValidationError("Order is not editable. Hold the order first.")

    menu_item_result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.variants)).where(MenuItem.id == payload.menu_item_id)
    )
    menu_item = menu_item_result.scalar_one_or_none()
    if menu_item is None:
        raise OrderNotFoundError("Menu item not found.")
    if not menu_item.is_available:
        raise OrderValidationError("Menu item is currently unavailable.")

    variant: MenuItemVariant | None = None
    if payload.variant_id is not None:
        variant = next((v for v in menu_item.variants if v.id == payload.variant_id and v.is_active), None)
        if variant is None:
            raise OrderValidationError("Variant not found or inactive.")
        unit_price = _to_money(variant.sell_price)
    elif menu_item.variants and any(v.is_active for v in menu_item.variants):
        raise OrderValidationError(f"'{menu_item.name}' has size options. Please select a size before adding.")
    else:
        unit_price = _to_money(menu_item.base_price)

    line_total = _to_money(unit_price * payload.quantity)

    db.add(
        PosOrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            variant_id=variant.id if variant else None,
            menu_item_name=menu_item.name,
            variant_name=variant.name if variant else None,
            quantity=payload.quantity,
            unit_price=unit_price,
            line_total=line_total,
            note=payload.note,
        )
    )
    await db.flush()

    order = await get_order(db, order.id)
    await _recompute_order_totals(db, order)
    await db.commit()
    return await get_order(db, order.id)


async def update_order_item(
    db: AsyncSession,
    order_id: int,
    item_id: int,
    payload: PosOrderItemUpdate,
) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status != PosOrderStatus.OPEN:
        raise OrderValidationError("Order is not editable. Hold the order first.")

    item = next((line for line in order.items if line.id == item_id), None)
    if item is None:
        raise OrderNotFoundError("Order item not found.")
    if item.is_voided:
        raise OrderValidationError("Cannot update a voided order item.")

    item.quantity = payload.quantity
    item.note = payload.note
    item.line_total = _to_money(item.unit_price * payload.quantity)
    await _recompute_order_totals(db, order)
    await db.commit()
    return await get_order(db, order.id)


async def void_order_item(
    db: AsyncSession,
    order_id: int,
    item_id: int,
    payload: PosOrderItemVoid,
) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status != PosOrderStatus.OPEN:
        raise OrderValidationError("Order is not editable. Hold the order first.")

    item = next((line for line in order.items if line.id == item_id), None)
    if item is None:
        raise OrderNotFoundError("Order item not found.")
    if item.is_voided:
        return order

    item.is_voided = True
    item.void_reason = payload.reason
    await _recompute_order_totals(db, order)
    await db.commit()
    return await get_order(db, order.id)


async def send_order(db: AsyncSession, order_id: int) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status != PosOrderStatus.OPEN:
        raise OrderValidationError("Only open orders can be sent.")
    if not any(not line.is_voided for line in order.items):
        raise OrderValidationError("Order must have at least one active item before sending.")

    order.status = PosOrderStatus.SENT
    await db.commit()
    return await get_order(db, order.id)


async def hold_order(db: AsyncSession, order_id: int) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status != PosOrderStatus.SENT:
        raise OrderValidationError("Only sent orders can be moved back to hold.")

    order.status = PosOrderStatus.OPEN
    await db.commit()
    return await get_order(db, order.id)


async def void_order(db: AsyncSession, order_id: int, reason: str | None = None) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status in [PosOrderStatus.CLOSED, PosOrderStatus.VOIDED]:
        raise OrderValidationError("Closed or voided orders cannot be voided again.")

    for item in order.items:
        if not item.is_voided:
            item.is_voided = True
            item.void_reason = reason or "Order voided."

    order.status = PosOrderStatus.VOIDED
    order.payment_method = None
    order.amount_paid = None
    order.closed_at = datetime.now(UTC)

    if order.table_id is not None:
        table_result = await db.execute(select(Table).where(Table.id == order.table_id))
        table = table_result.scalar_one_or_none()
        if table is not None:
            table.status = TableStatus.AVAILABLE

    await _recompute_order_totals(db, order)
    await db.commit()
    return await get_order(db, order.id)


async def close_order(db: AsyncSession, order_id: int, payload: PosOrderClose) -> PosOrder:
    order = await get_order(db, order_id)
    if order.status in [PosOrderStatus.CLOSED, PosOrderStatus.VOIDED]:
        raise OrderValidationError("This order is already finalized.")

    if order.total_amount <= Decimal("0.00"):
        raise OrderValidationError("Cannot close an empty order.")
    if payload.amount_paid < order.total_amount:
        raise OrderValidationError("Amount paid is less than order total.")

    order.status = PosOrderStatus.CLOSED
    order.payment_method = payload.payment_method
    order.amount_paid = _to_money(payload.amount_paid)
    order.closed_at = datetime.now(UTC)

    db.add(
        PosPayment(
            order_id=order.id,
            method=payload.payment_method,
            amount=order.amount_paid,
            reference=None,
            paid_at=order.closed_at,
        )
    )

    if order.table_id is not None:
        table_result = await db.execute(select(Table).where(Table.id == order.table_id))
        table = table_result.scalar_one_or_none()
        if table is not None:
            table.status = TableStatus.AVAILABLE

    await db.commit()
    return await get_order(db, order.id)
