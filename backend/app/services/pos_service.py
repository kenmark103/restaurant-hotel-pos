"""
pos_service.py — POS order lifecycle  (final)
─────────────────────────────────────────────────────────────────────────────
Scope after extraction:
  • Order CRUD (create → add items → send → pay → close)
  • Item quantity update / remove (unsent items)
  • Item-level and order-level void
  • Discount application / removal
  • Bill splitting (multiple checks from one order)
  • Table merge (coordinates two orders)

Table management → table_service.py
Cash sessions    → cash_service.py

Bug fixes applied:
  • send_to_kitchen: station_ids collected inside loop (not stale outer var)
  • Multi-station routing via MenuItem.stations M2M (kitchen_station_id fallback)
  • _recalculate_totals: reads tax from DB settings, handles inclusive + exclusive
  • PosOrderItem uses kds_tickets list (one-to-many), not single kds_ticket_id FK
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.event_bus import (
    EventBus,
    OrderClosed,
    OrderItemVoided,
    OrderSentToStations,
    PaymentRecorded,
    PrintRequested,
)
from app.db.models import (
    BranchSettings,
    DiscountType,
    KdsTicket,
    KdsTicketStatus,
    MenuItem,
    MenuModifierOption,
    OrderDiscount,
    OrderType,
    PaymentMethod,
    PosOrder,
    PosOrderItem,
    PosOrderItemModifier,
    PosOrderStatus,
    PosPayment,
    PrintJobType,
    Table,
    TableStatus,
    VenueSettings,
)
from app.services.base import BaseService, NotFoundError, ValidationError, to_money
from app.services.inventory_service import InventoryService


class POSService(BaseService[PosOrder]):
    model = PosOrder

    def __init__(
        self,
        db,
        current_user=None,
        websocket_manager=None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        super().__init__(db, current_user)
        self.ws = websocket_manager
        self.bus = event_bus
        self.inventory = InventoryService(db, current_user)
        self._tax_rate_cache: Optional[Decimal] = None
        self._tax_inclusive_cache: Optional[bool] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _publish(self, event) -> None:
        if self.bus:
            await self.bus.publish(event)

    async def _get_tax_params(self, branch_id: int) -> tuple[Decimal, bool]:
        if self._tax_rate_cache is not None:
            return self._tax_rate_cache, self._tax_inclusive_cache  # type: ignore[return-value]

        branch_settings = await self.db.scalar(
            select(BranchSettings).where(BranchSettings.branch_id == branch_id)
        )
        venue = await self.db.scalar(select(VenueSettings))
        base_rate = Decimal("16.00")
        inclusive = True
        if venue:
            base_rate = Decimal(str(venue.tax_rate))
            inclusive = venue.tax_inclusive
        if branch_settings and branch_settings.tax_rate is not None:
            base_rate = Decimal(str(branch_settings.tax_rate))
        self._tax_rate_cache = base_rate / 100
        self._tax_inclusive_cache = inclusive
        return self._tax_rate_cache, self._tax_inclusive_cache  # type: ignore[return-value]

    async def _recalculate_totals(self, order: PosOrder) -> None:
        active_items = [i for i in order.items if not i.is_voided]
        subtotal = to_money(sum(i.line_total for i in active_items))
        order.subtotal = subtotal

        tax_rate, tax_inclusive = await self._get_tax_params(order.branch_id)
        if tax_inclusive:
            order.tax_amount = to_money(subtotal - subtotal / (1 + tax_rate))
        else:
            order.tax_amount = to_money(subtotal * tax_rate)

        order.discount_total = to_money(sum(d.amount for d in order.discounts))

        if tax_inclusive:
            order.total_amount = to_money(max(subtotal - order.discount_total, Decimal("0")))
        else:
            order.total_amount = to_money(
                max(subtotal + order.tax_amount - order.discount_total, Decimal("0"))
            )

    async def get_order_with_items(self, order_id: int) -> PosOrder:
        result = await self.db.execute(
            select(PosOrder)
            .options(
                selectinload(PosOrder.items).selectinload(PosOrderItem.modifiers),
                selectinload(PosOrder.items).selectinload(PosOrderItem.kds_tickets),
                selectinload(PosOrder.discounts),
                selectinload(PosOrder.payments),
                selectinload(PosOrder.table),
                selectinload(PosOrder.staff_user),
            )
            .where(PosOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("PosOrder")
        return order

    async def _get_active_table_order(self, table_id: int) -> Optional[PosOrder]:
        return await self.db.scalar(
            select(PosOrder).where(
                PosOrder.table_id == table_id,
                PosOrder.status.in_((PosOrderStatus.OPEN, PosOrderStatus.SENT)),
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Create / list
    # ─────────────────────────────────────────────────────────────────────────

    async def create_order(
        self,
        order_type: OrderType,
        staff_user_id: int,
        branch_id: Optional[int] = None,
        table_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        room_number: Optional[str] = None,
        note: Optional[str] = None,
    ) -> PosOrder:
        if order_type == OrderType.DINE_IN and table_id:
            existing = await self._get_active_table_order(table_id)
            if existing:
                return existing
            table = await self.db.get(Table, table_id)
            if not table:
                raise NotFoundError("Table")
            if table.status == TableStatus.RESERVED:
                raise ValidationError("Table is reserved — check in via reservations first")
            table.status = TableStatus.OCCUPIED
            branch_id = table.branch_id

        if not branch_id:
            raise ValidationError("branch_id is required for non-dine-in orders")

        order = PosOrder(
            branch_id=branch_id, table_id=table_id, staff_user_id=staff_user_id,
            order_type=order_type, status=PosOrderStatus.OPEN,
            customer_name=customer_name, customer_phone=customer_phone,
            room_number=room_number, note=note,
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)

        if self.ws and table_id:
            await self.ws.notify_table_status(branch_id, table_id, "occupied")

        return order

    async def get_orders(
        self,
        branch_id: int,
        status: Optional[PosOrderStatus] = None,
        order_type: Optional[OrderType] = None,
        staff_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PosOrder]:
        query = (
            select(PosOrder)
            .options(
                selectinload(PosOrder.items),
                selectinload(PosOrder.table),
                selectinload(PosOrder.payments),
            )
            .where(PosOrder.branch_id == branch_id)
            .order_by(PosOrder.created_at.desc())
            .offset(skip).limit(limit)
        )
        if status:
            query = query.where(PosOrder.status == status)
        if order_type:
            query = query.where(PosOrder.order_type == order_type)
        if staff_user_id:
            query = query.where(PosOrder.staff_user_id == staff_user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # Items
    # ─────────────────────────────────────────────────────────────────────────

    async def add_item(
        self,
        order_id: int,
        menu_item_id: int,
        quantity: int = 1,
        variant_id: Optional[int] = None,
        modifier_option_ids: Optional[List[int]] = None,
        note: Optional[str] = None,
    ) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status in (PosOrderStatus.CLOSED, PosOrderStatus.VOIDED):
            raise ValidationError(f"Cannot add items to a {order.status} order")
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1")

        result = await self.db.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.variants))
            .where(MenuItem.id == menu_item_id)
        )
        menu_item = result.scalar_one_or_none()
        if not menu_item:
            raise NotFoundError("MenuItem")
        if not menu_item.is_available:
            raise ValidationError(f"'{menu_item.name}' is not currently available")

        unit_price = menu_item.base_price
        variant_name: Optional[str] = None
        active_variants = [v for v in menu_item.variants if v.is_active]

        if variant_id:
            variant = next((v for v in active_variants if v.id == variant_id), None)
            if not variant:
                raise NotFoundError("Variant")
            unit_price = variant.sell_price
            variant_name = variant.name
        elif active_variants:
            raise ValidationError(f"'{menu_item.name}' requires a variant selection")

        modifier_cost = Decimal("0.00")
        order_modifiers: List[PosOrderItemModifier] = []
        if modifier_option_ids:
            for opt_id in modifier_option_ids:
                opt = await self.db.get(MenuModifierOption, opt_id)
                if opt and opt.is_available:
                    modifier_cost += opt.price_delta
                    order_modifiers.append(PosOrderItemModifier(
                        option_id=opt.id, option_name=opt.name, price_delta=opt.price_delta
                    ))

        order_item = PosOrderItem(
            order_id=order_id, menu_item_id=menu_item_id, variant_id=variant_id,
            menu_item_name=menu_item.name, variant_name=variant_name,
            quantity=quantity, unit_price=unit_price,
            line_total=to_money((unit_price + modifier_cost) * quantity),
            note=note, modifiers=order_modifiers,
        )
        self.db.add(order_item)
        order.items.append(order_item)
        await self._recalculate_totals(order)
        await self.db.commit()

        if self.ws:
            await self.ws.notify_order_update(
                order_id, {"type": "item_added", "item": menu_item.name, "qty": quantity}
            )

        return await self.get_order_with_items(order_id)

    async def update_item_quantity(self, order_id: int, item_id: int, quantity: int) -> PosOrder:
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1")
        order = await self.get_order_with_items(order_id)
        if order.status != PosOrderStatus.OPEN:
            raise ValidationError("Quantity can only be changed on OPEN orders")
        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("OrderItem")
        if item.is_voided:
            raise ValidationError("Cannot update a voided item")
        if item.sent_to_kitchen:
            raise ValidationError("Item already sent — void and re-add to change quantity")

        modifier_cost = sum(m.price_delta for m in item.modifiers)
        item.quantity = quantity
        item.line_total = to_money((item.unit_price + modifier_cost) * quantity)
        await self._recalculate_totals(order)
        await self.db.commit()
        return await self.get_order_with_items(order_id)

    async def remove_item(self, order_id: int, item_id: int) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status != PosOrderStatus.OPEN:
            raise ValidationError("Use void_item for sent orders")
        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("OrderItem")
        if item.sent_to_kitchen:
            raise ValidationError("Item already sent — use void_item instead")
        await self.db.delete(item)
        order.items = [i for i in order.items if i.id != item_id]
        await self._recalculate_totals(order)
        await self.db.commit()
        return await self.get_order_with_items(order_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Void
    # ─────────────────────────────────────────────────────────────────────────

    async def void_item(self, order_id: int, item_id: int, reason: str) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status in (PosOrderStatus.CLOSED, PosOrderStatus.VOIDED):
            raise ValidationError(f"Cannot void items on a {order.status} order")
        if not reason:
            raise ValidationError("Void reason is required")

        item = next((i for i in order.items if i.id == item_id), None)
        if not item:
            raise NotFoundError("OrderItem")
        if item.is_voided:
            raise ValidationError("Item is already voided")

        for ticket in item.kds_tickets:
            if ticket.status not in (KdsTicketStatus.SERVED, KdsTicketStatus.CANCELLED):
                ticket.status = KdsTicketStatus.CANCELLED

        if item.sent_to_kitchen:
            await self.inventory.reverse_sale_movement(
                branch_id=order.branch_id, menu_item_id=item.menu_item_id,
                quantity=Decimal(str(item.quantity)), order_id=order.id, variant_id=item.variant_id,
            )

        item.is_voided = True
        item.void_reason = reason
        item.voided_at = datetime.now(UTC)
        item.voided_by_id = self.user.id if self.user else None

        await self._recalculate_totals(order)
        await self.db.commit()

        await self._publish(OrderItemVoided(
            order_id=order_id, order_item_id=item_id,
            menu_item_name=item.menu_item_name, quantity=item.quantity,
            reason=reason, voided_by_id=self.user.id if self.user else 0,
            branch_id=order.branch_id,
        ))
        if self.ws:
            await self.ws.notify_order_update(order_id, {"type": "item_voided", "item_id": item_id})

        return await self.get_order_with_items(order_id)

    async def void_order(self, order_id: int, reason: str) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status == PosOrderStatus.CLOSED:
            raise ValidationError("Cannot void a closed order — process a refund instead")
        if order.status == PosOrderStatus.VOIDED:
            raise ValidationError("Order is already voided")
        if not reason:
            raise ValidationError("Void reason is required")

        for item in order.items:
            if item.is_voided:
                continue
            for ticket in item.kds_tickets:
                if ticket.status not in (KdsTicketStatus.SERVED, KdsTicketStatus.CANCELLED):
                    ticket.status = KdsTicketStatus.CANCELLED
            if item.sent_to_kitchen:
                await self.inventory.reverse_sale_movement(
                    branch_id=order.branch_id, menu_item_id=item.menu_item_id,
                    quantity=Decimal(str(item.quantity)), order_id=order.id, variant_id=item.variant_id,
                )
            item.is_voided = True
            item.void_reason = reason
            item.voided_at = datetime.now(UTC)
            item.voided_by_id = self.user.id if self.user else None

        order.status = PosOrderStatus.VOIDED
        if order.table_id:
            table = await self.db.get(Table, order.table_id)
            if table:
                table.status = TableStatus.CLEANING

        await self.db.commit()

        await self._publish(OrderItemVoided(
            order_id=order_id, order_item_id=0,
            menu_item_name="[ENTIRE ORDER]", quantity=0,
            reason=reason, voided_by_id=self.user.id if self.user else 0,
            branch_id=order.branch_id,
        ))
        if self.ws:
            await self.ws.notify_order_update(order_id, {"type": "order_voided"})
            if order.table_id:
                await self.ws.notify_table_status(order.branch_id, order.table_id, "cleaning")

        return order

    # ─────────────────────────────────────────────────────────────────────────
    # Send to kitchen
    # ─────────────────────────────────────────────────────────────────────────

    async def send_to_kitchen(
        self, order_id: int, station_filter: Optional[str] = None
    ) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status in (PosOrderStatus.CLOSED, PosOrderStatus.VOIDED):
            raise ValidationError(f"Order is {order.status}")

        unsent = [i for i in order.items if not i.sent_to_kitchen and not i.is_voided]
        if not unsent:
            raise ValidationError("No new items to send to kitchen")

        auto_deplete = await self.inventory.is_auto_depletion_enabled()
        notified_station_ids: set[str] = set()
        sent_item_ids: list[int] = []

        for item in unsent:
            mi_result = await self.db.execute(
                select(MenuItem).options(selectinload(MenuItem.stations)).where(MenuItem.id == item.menu_item_id)
            )
            menu_item = mi_result.scalar_one_or_none()

            if menu_item and menu_item.stations:
                item_stations = [
                    s.id for s in menu_item.stations
                    if s.is_active and (station_filter is None or s.id == station_filter)
                ]
            else:
                primary = (menu_item.kitchen_station_id if menu_item else None) or "any"
                item_stations = [primary] if (station_filter is None or primary == station_filter) else []

            if not item_stations:
                item.sent_to_kitchen = True
                sent_item_ids.append(item.id)
                continue

            modifiers_text = ", ".join(m.option_name for m in item.modifiers) if item.modifiers else None

            for station_id in item_stations:                         # ← local var, not outer `ticket`
                self.db.add(KdsTicket(
                    order_id=order.id, order_item_id=item.id,
                    menu_item_id=item.menu_item_id, station_id=station_id,
                    item_name=item.menu_item_name, quantity=item.quantity,
                    note=item.note, modifiers_text=modifiers_text, priority=0,
                    sent_at=datetime.now(UTC),
                    estimated_prep_time=menu_item.prep_time_minutes if menu_item else 10,
                ))
                notified_station_ids.add(station_id)                 # ← collected safely inside loop

            item.sent_to_kitchen = True
            sent_item_ids.append(item.id)

            if auto_deplete:
                await self.inventory.record_sale_movement(
                    branch_id=order.branch_id, menu_item_id=item.menu_item_id,
                    quantity=Decimal(str(item.quantity)), order_id=order.id, variant_id=item.variant_id,
                )

        order.status = PosOrderStatus.SENT
        await self.db.commit()

        await self._publish(OrderSentToStations(
            order_id=order.id, branch_id=order.branch_id,
            station_ids=list(notified_station_ids), item_ids=sent_item_ids,
        ))
        if self.ws:
            label = order.table.table_number if order.table else "Counter"
            for sid in notified_station_ids:
                await self.ws.notify_kitchen(
                    order.branch_id, sid,
                    {"type": "new_tickets", "order_id": order.id, "table": label},
                )

        return await self.get_order_with_items(order_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Close / pay
    # ─────────────────────────────────────────────────────────────────────────

    async def close_order(
        self,
        order_id: int,
        payment_method: PaymentMethod,
        amount_paid: Decimal,
        split_payments: Optional[List[Dict]] = None,
    ) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status == PosOrderStatus.CLOSED:
            raise ValidationError("Order is already closed")
        if order.status == PosOrderStatus.VOIDED:
            raise ValidationError("Cannot close a voided order")
        if order.total_amount <= 0:
            raise ValidationError("Cannot close an empty order")

        recorded: list[dict] = []

        if split_payments:
            tendered = sum(to_money(p["amount"]) for p in split_payments)
            if tendered < order.total_amount:
                raise ValidationError(f"Insufficient: need {order.total_amount}, tendered {tendered}")
            for pmt in split_payments:
                self.db.add(PosPayment(
                    order_id=order_id, method=PaymentMethod(pmt["method"]),
                    amount=to_money(pmt["amount"]), reference=pmt.get("reference"),
                ))
                recorded.append(pmt)
            primary = max(split_payments, key=lambda p: to_money(p["amount"]))
            order.payment_method = PaymentMethod(primary["method"])
            order.amount_paid = tendered
            order.change_due = to_money(tendered - order.total_amount)
        else:
            if amount_paid < order.total_amount:
                raise ValidationError(f"Insufficient: need {order.total_amount}, paid {amount_paid}")
            self.db.add(PosPayment(order_id=order_id, method=payment_method, amount=to_money(amount_paid)))
            recorded.append({"method": payment_method.value, "amount": str(amount_paid)})
            order.payment_method = payment_method
            order.amount_paid = to_money(amount_paid)
            order.change_due = to_money(amount_paid - order.total_amount)

        order.status = PosOrderStatus.CLOSED
        order.closed_at = datetime.now(UTC)
        if order.table_id:
            table = await self.db.get(Table, order.table_id)
            if table:
                table.status = TableStatus.CLEANING

        await self.db.commit()

        await self._publish(OrderClosed(
            order_id=order.id, branch_id=order.branch_id,
            total_amount=order.total_amount, payments=recorded, staff_user_id=order.staff_user_id,
        ))
        for pmt in recorded:
            await self._publish(PaymentRecorded(
                order_id=order.id, branch_id=order.branch_id,
                method=pmt["method"], amount=Decimal(str(pmt["amount"])),
                reference=pmt.get("reference"),
            ))
        await self._publish(PrintRequested(
            job_type=PrintJobType.RECEIPT, order_id=order.id,
            branch_id=order.branch_id, requested_by_id=order.staff_user_id,
            payload_snapshot={"order_id": order.id, "total": str(order.total_amount)},
        ))

        if self.ws:
            await self.ws.notify_order_update(order_id, {"type": "order_closed"})
            if order.table_id:
                await self.ws.notify_table_status(order.branch_id, order.table_id, "cleaning")

        return await self.get_order_with_items(order_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Discounts
    # ─────────────────────────────────────────────────────────────────────────

    async def apply_discount(
        self,
        order_id: int,
        discount_type: DiscountType,
        value: Decimal,
        order_item_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> PosOrder:
        order = await self.get_order_with_items(order_id)
        if order.status in (PosOrderStatus.CLOSED, PosOrderStatus.VOIDED):
            raise ValidationError("Cannot discount a closed/voided order")
        if value <= 0:
            raise ValidationError("Discount value must be positive")

        base_amount = order.subtotal
        if order_item_id:
            item = next((i for i in order.items if i.id == order_item_id), None)
            if not item:
                raise NotFoundError("OrderItem")
            if item.is_voided:
                raise ValidationError("Cannot discount a voided item")
            base_amount = item.line_total

        if discount_type == DiscountType.PERCENT:
            if value > 100:
                raise ValidationError("Percentage discount cannot exceed 100%")
            amount = to_money(base_amount * value / 100)
        else:
            amount = to_money(min(value, base_amount))

        discount = OrderDiscount(
            order_id=order_id, order_item_id=order_item_id,
            discount_type=discount_type, value=value, amount=amount,
            reason=reason, authorized_by_user_id=self.user.id if self.user else None,
        )
        self.db.add(discount)
        order.discounts.append(discount)
        await self._recalculate_totals(order)
        await self.db.commit()
        return await self.get_order_with_items(order_id)

    async def remove_discount(self, order_id: int, discount_id: int) -> PosOrder:
        discount = await self.db.get(OrderDiscount, discount_id)
        if not discount or discount.order_id != order_id:
            raise NotFoundError("Discount")
        await self.db.delete(discount)
        order = await self.get_order_with_items(order_id)
        await self._recalculate_totals(order)
        await self.db.commit()
        return await self.get_order_with_items(order_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Bill split + table merge
    # ─────────────────────────────────────────────────────────────────────────

    async def split_bill(self, order_id: int, splits: List[Dict]) -> List[PosOrder]:
        original = await self.get_order_with_items(order_id)
        if original.status in (PosOrderStatus.CLOSED, PosOrderStatus.VOIDED):
            raise ValidationError(f"Cannot split a {original.status} order")

        active_items = {i.id: i for i in original.items if not i.is_voided}
        assigned: set[int] = set()
        for split in splits:
            for iid in split.get("item_ids", []):
                if iid not in active_items:
                    raise ValidationError(f"Item {iid} not found or is voided")
                if iid in assigned:
                    raise ValidationError(f"Item {iid} appears in multiple splits")
                assigned.add(iid)

        tax_rate, tax_inclusive = await self._get_tax_params(original.branch_id)
        new_orders: List[PosOrder] = []

        for split in splits:
            child = PosOrder(
                branch_id=original.branch_id, table_id=original.table_id,
                staff_user_id=original.staff_user_id, order_type=original.order_type,
                status=original.status, customer_name=split.get("customer_name"),
                note=original.note,
            )
            self.db.add(child)
            await self.db.flush()

            split_items = [active_items[iid] for iid in split.get("item_ids", [])]
            for item in split_items:
                item.order_id = child.id

            child.subtotal = to_money(sum(i.line_total for i in split_items))
            if tax_inclusive:
                child.tax_amount = to_money(child.subtotal - child.subtotal / (1 + tax_rate))
                child.total_amount = child.subtotal
            else:
                child.tax_amount = to_money(child.subtotal * tax_rate)
                child.total_amount = to_money(child.subtotal + child.tax_amount)
            child.discount_total = Decimal("0.00")
            new_orders.append(child)

        original.status = PosOrderStatus.VOIDED
        await self.db.commit()
        return new_orders

    # ─────────────────────────────────────────────────────────────────────────
    # Manager override  (blueprint §4.4)
    # ─────────────────────────────────────────────────────────────────────────

    async def request_manager_override(
        self,
        branch_id: int,
        action: str,
        manager_pin: str,
        requesting_user_id: int,
        entity_type: str | None = None,
        entity_id: int | None = None,
        reason: str | None = None,
    ):
        """
        Proxy to OverrideService.  POSService is the natural entry-point for
        override requests because the cashier initiates them from the POS screen.
        """
        from app.db.models import OverrideAction
        from app.services.override_service import OverrideService

        svc = OverrideService(self.db, self.user)
        return await svc.request_grant(
            requesting_user_id=requesting_user_id,
            branch_id=branch_id,
            action=OverrideAction(action),
            manager_pin=manager_pin,
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Bulk offline sync  (frontend blueprint §7 — drain IndexedDB queue)
    # ─────────────────────────────────────────────────────────────────────────

    async def bulk_sync_offline_orders(self, orders: list[dict]) -> list[dict]:
        """
        Accept a batch of orders that were created offline on the client.

        Each entry may contain:
          { order_type, branch_id, table_id, customer_name, customer_phone,
            room_number, note, client_id (temporary cuid2), items: [...] }

        Returns a list of { client_id, order_id, status } so the client can
        replace its temporary IDs with real server IDs.
        """
        results = []
        for order_data in orders:
            client_id = order_data.pop("client_id", None)
            items = order_data.pop("items", [])
            try:
                order = await self.create_order(
                    order_type=order_data.get("order_type", "dine_in"),
                    staff_user_id=self.user.id if self.user else order_data.get("staff_user_id", 0),
                    branch_id=order_data.get("branch_id"),
                    table_id=order_data.get("table_id"),
                    customer_name=order_data.get("customer_name"),
                    customer_phone=order_data.get("customer_phone"),
                    room_number=order_data.get("room_number"),
                    note=order_data.get("note"),
                )
                for item in items:
                    await self.add_item(
                        order_id=order.id,
                        menu_item_id=item["menu_item_id"],
                        quantity=item.get("quantity", 1),
                        variant_id=item.get("variant_id"),
                        modifier_option_ids=item.get("modifier_option_ids"),
                        note=item.get("note"),
                    )
                results.append({
                    "client_id": client_id,
                    "order_id": order.id,
                    "status": "synced",
                })
            except Exception as exc:
                results.append({
                    "client_id": client_id,
                    "order_id": None,
                    "status": "failed",
                    "error": str(exc),
                })
        return results

    async def merge_tables(self, primary_table_id: int, secondary_table_id: int) -> PosOrder:
        primary_order = await self._get_active_table_order(primary_table_id)
        secondary_order = await self._get_active_table_order(secondary_table_id)
        if not primary_order:
            raise NotFoundError("Active order for primary table")
        if not secondary_order:
            raise NotFoundError("Active order for secondary table")
        if primary_order.id == secondary_order.id:
            raise ValidationError("Cannot merge a table with itself")

        primary_order = await self.get_order_with_items(primary_order.id)
        secondary_order = await self.get_order_with_items(secondary_order.id)

        for item in secondary_order.items:
            if not item.is_voided:
                item.order_id = primary_order.id

        secondary_order.status = PosOrderStatus.VOIDED
        secondary_table = await self.db.get(Table, secondary_table_id)
        if secondary_table:
            secondary_table.status = TableStatus.AVAILABLE

        await self.db.flush()
        primary_order = await self.get_order_with_items(primary_order.id)
        await self._recalculate_totals(primary_order)
        await self.db.commit()

        if self.ws and secondary_table:
            await self.ws.notify_table_status(secondary_table.branch_id, secondary_table_id, "available")

        return await self.get_order_with_items(primary_order.id)