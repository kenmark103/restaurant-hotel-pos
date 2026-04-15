"""
inventory_service.py — Stock tracking & inventory control
─────────────────────────────────────────────────────────────────────────────
Covers:
  • Real-time stock levels (denormalized + ledger aggregate)
  • Immutable movement ledger (sale / purchase / adjustment / waste / transfer)
  • Manual stock adjustments with full audit trail
  • Purchase / goods-receiving workflow
  • Dedicated waste-logging
  • Low-stock detection
  • Policy management

Bug fixes from original:
  • adjust_stock: db.flush() before referencing adjustment.id
  • add_stock_movement: uses AuditMixin field created_by_id (not created_by_user_id)
"""
from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.models import (
    InventoryPolicy,
    MenuItem,
    MenuItemVariant,
    StockAdjustment,
    StockMovement,
    StockMovementType,
)
from app.services.base import BaseService, NotFoundError, ValidationError, to_money


class InventoryService(BaseService[StockMovement]):
    model = StockMovement

    # ═══════════════════════════════════════════════════════════════════════════
    # STOCK LEVELS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_stock_levels(
        self,
        branch_id: int,
        low_stock_only: bool = False,
    ) -> List[dict]:
        """
        Returns current stock per tracked item/variant at a branch.
        Uses the denormalized ``current_stock`` field for speed;
        falls back to ledger aggregation for accuracy if needed.
        """
        query = (
            select(MenuItem)
            .options(selectinload(MenuItem.variants), selectinload(MenuItem.unit_of_measure))
            .where(MenuItem.track_inventory == True)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        levels = []
        for item in items:
            if item.variants:
                for variant in item.variants:
                    if not variant.is_active:
                        continue
                    current = to_money(variant.current_stock)
                    threshold = item.low_stock_threshold or 10
                    is_low = current <= threshold
                    if low_stock_only and not is_low:
                        continue
                    levels.append({
                        "menu_item_id": item.id,
                        "variant_id": variant.id,
                        "name": item.name,
                        "variant_name": variant.name,
                        "current_stock": current,
                        "unit": item.unit_of_measure_id,
                        "low_stock_threshold": threshold,
                        "is_low": is_low,
                        "cost_price": variant.cost_price or item.cost_price,
                    })
            else:
                current = to_money(item.current_stock)
                threshold = item.low_stock_threshold or 10
                is_low = current <= threshold
                if low_stock_only and not is_low:
                    continue
                levels.append({
                    "menu_item_id": item.id,
                    "variant_id": None,
                    "name": item.name,
                    "variant_name": None,
                    "current_stock": current,
                    "unit": item.unit_of_measure_id,
                    "low_stock_threshold": threshold,
                    "is_low": is_low,
                    "cost_price": item.cost_price,
                })

        return levels

    async def get_low_stock_items(self, branch_id: int) -> List[dict]:
        """Convenience shortcut — returns only items below their threshold."""
        return await self.get_stock_levels(branch_id, low_stock_only=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # STOCK MOVEMENT LEDGER  (immutable write)
    # ═══════════════════════════════════════════════════════════════════════════

    async def add_stock_movement(
        self,
        branch_id: int,
        menu_item_id: int,
        quantity: Decimal,          # positive = stock in, negative = stock out
        movement_type: StockMovementType,
        variant_id: Optional[int] = None,
        unit_cost: Optional[Decimal] = None,
        reference_type: Optional[str] = None,   # 'order' | 'purchase' | 'adjustment' | 'waste'
        reference_id: Optional[int] = None,
        notes: Optional[str] = None,
        batch_number: Optional[str] = None,
        expiry_date=None,
    ) -> StockMovement:
        """
        Core ledger write.  Every stock change must flow through here.

        Note: uses AuditMixin field ``created_by_id`` (not created_by_user_id).
        """
        movement = StockMovement(
            branch_id=branch_id,
            menu_item_id=menu_item_id,
            variant_id=variant_id,
            quantity=quantity,
            movement_type=movement_type,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            batch_number=batch_number,
            expiry_date=expiry_date,
            created_by_id=self.user.id if self.user else None,  # AuditMixin field
        )
        self.db.add(movement)

        # Update denormalized stock on the item / variant for fast reads
        item = await self.db.get(MenuItem, menu_item_id)
        if item:
            if variant_id:
                variant = await self.db.get(MenuItemVariant, variant_id)
                if variant:
                    variant.current_stock = to_money(
                        Decimal(str(variant.current_stock)) + quantity
                    )
            else:
                item.current_stock = to_money(
                    Decimal(str(item.current_stock)) + quantity
                )

        await self.db.commit()
        await self.db.refresh(movement)
        return movement

    # ═══════════════════════════════════════════════════════════════════════════
    # SALE DEPLETION  (called by POSService.send_to_kitchen)
    # ═══════════════════════════════════════════════════════════════════════════

    async def record_sale_movement(
        self,
        branch_id: int,
        menu_item_id: int,
        quantity: Decimal,   # positive — will be negated internally
        order_id: int,
        variant_id: Optional[int] = None,
    ) -> Optional[StockMovement]:
        """Auto-deduct stock when an order is sent to the kitchen.  No-ops if item
        doesn't track inventory."""
        item = await self.db.get(MenuItem, menu_item_id)
        if not item or not item.track_inventory:
            return None

        return await self.add_stock_movement(
            branch_id=branch_id,
            menu_item_id=menu_item_id,
            variant_id=variant_id,
            quantity=-abs(quantity),   # always out
            movement_type=StockMovementType.SALE,
            reference_type="order",
            reference_id=order_id,
        )

    async def reverse_sale_movement(
        self,
        branch_id: int,
        menu_item_id: int,
        quantity: Decimal,
        order_id: int,
        variant_id: Optional[int] = None,
    ) -> Optional[StockMovement]:
        """Reversal when a sent order item is voided — adds stock back."""
        item = await self.db.get(MenuItem, menu_item_id)
        if not item or not item.track_inventory:
            return None

        return await self.add_stock_movement(
            branch_id=branch_id,
            menu_item_id=menu_item_id,
            variant_id=variant_id,
            quantity=abs(quantity),    # back in
            movement_type=StockMovementType.RETURN_IN,
            reference_type="order",
            reference_id=order_id,
            notes="Void reversal",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PURCHASE RECEIVING  (goods-receiving note)
    # ═══════════════════════════════════════════════════════════════════════════

    async def receive_stock(
        self,
        branch_id: int,
        items: List[dict],   # [{menu_item_id, quantity, unit_cost, variant_id?, batch_number?, expiry_date?}]
        supplier_reference: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> List[StockMovement]:
        """
        Bulk goods-receiving entry.  Creates one StockMovement per line.

        ``items`` example::

            [
                {"menu_item_id": 1, "quantity": "50", "unit_cost": "120.00"},
                {"menu_item_id": 2, "quantity": "10", "unit_cost": "850.00", "variant_id": 5},
            ]
        """
        if not items:
            raise ValidationError("At least one item is required")

        movements = []
        for line in items:
            menu_item_id = line["menu_item_id"]
            quantity = Decimal(str(line["quantity"]))
            if quantity <= 0:
                raise ValidationError(f"Quantity must be positive for item {menu_item_id}")

            unit_cost = Decimal(str(line["unit_cost"])) if line.get("unit_cost") else None

            movement = await self.add_stock_movement(
                branch_id=branch_id,
                menu_item_id=menu_item_id,
                variant_id=line.get("variant_id"),
                quantity=quantity,
                movement_type=StockMovementType.PURCHASE,
                unit_cost=unit_cost,
                reference_type="purchase",
                notes=f"GRN {supplier_reference or 'manual'}: {notes or ''}".strip(": "),
                batch_number=line.get("batch_number"),
                expiry_date=line.get("expiry_date"),
            )
            movements.append(movement)

        return movements

    # ═══════════════════════════════════════════════════════════════════════════
    # WASTE LOGGING
    # ═══════════════════════════════════════════════════════════════════════════

    async def log_waste(
        self,
        branch_id: int,
        menu_item_id: int,
        quantity: Decimal,
        reason: str,
        variant_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """
        Record spoilage, breakage, or complimentary items.
        Keeps stock counts accurate and surfaces waste patterns in reporting.
        """
        if quantity <= 0:
            raise ValidationError("Waste quantity must be positive")
        if not reason:
            raise ValidationError("Waste reason is required")

        item = await self.db.get(MenuItem, menu_item_id)
        if not item:
            raise NotFoundError("MenuItem")

        return await self.add_stock_movement(
            branch_id=branch_id,
            menu_item_id=menu_item_id,
            variant_id=variant_id,
            quantity=-abs(quantity),
            movement_type=StockMovementType.WASTE,
            reference_type="waste",
            notes=f"{reason}. {notes or ''}".strip(". "),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL ADJUSTMENT  (stock-count correction)
    # ═══════════════════════════════════════════════════════════════════════════

    async def adjust_stock(
        self,
        branch_id: int,
        menu_item_id: int,
        new_quantity: Decimal,
        reason: str,
        variant_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> StockAdjustment:
        """
        Physical stock count correction.
        Creates an immutable adjustment record + a compensating StockMovement.

        Bug fix: db.flush() before referencing adjustment.id so the FK is set.
        """
        item = await self.db.get(MenuItem, menu_item_id)
        if not item:
            raise NotFoundError("MenuItem")

        # Current quantity from ledger (source of truth)
        ledger_qty = await self.db.scalar(
            select(func.coalesce(func.sum(StockMovement.quantity), 0))
            .where(
                StockMovement.branch_id == branch_id,
                StockMovement.menu_item_id == menu_item_id,
                StockMovement.variant_id == variant_id,
            )
        )
        current_qty = Decimal(str(ledger_qty))

        # Write adjustment record first, flush to obtain its PK
        adjustment = StockAdjustment(
            branch_id=branch_id,
            menu_item_id=menu_item_id,
            variant_id=variant_id,
            quantity_before=current_qty,
            quantity_after=new_quantity,
            reason=reason,
            notes=notes,
            created_by_id=self.user.id if self.user else None,  # AuditMixin field
        )
        self.db.add(adjustment)
        await self.db.flush()  # ← critical: ensures adjustment.id is populated

        # Create compensating movement (only if there is a difference)
        difference = new_quantity - current_qty
        if difference != 0:
            await self.add_stock_movement(
                branch_id=branch_id,
                menu_item_id=menu_item_id,
                variant_id=variant_id,
                quantity=difference,
                movement_type=StockMovementType.ADJUSTMENT,
                reference_type="adjustment",
                reference_id=adjustment.id,  # now valid
                notes=f"Stock adjustment: {reason}",
            )
        else:
            # No movement needed — still commit the adjustment record
            await self.db.commit()

        return adjustment

    # ═══════════════════════════════════════════════════════════════════════════
    # MOVEMENT HISTORY  (audit trail)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_movement_history(
        self,
        branch_id: int,
        menu_item_id: Optional[int] = None,
        movement_type: Optional[StockMovementType] = None,
        limit: int = 100,
    ) -> List[StockMovement]:
        query = (
            select(StockMovement)
            .options(
                selectinload(StockMovement.menu_item),
                selectinload(StockMovement.variant),
            )
            .where(StockMovement.branch_id == branch_id)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
        )
        if menu_item_id:
            query = query.where(StockMovement.menu_item_id == menu_item_id)
        if movement_type:
            query = query.where(StockMovement.movement_type == movement_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_adjustment_history(
        self,
        branch_id: int,
        limit: int = 50,
    ) -> List[StockAdjustment]:
        query = (
            select(StockAdjustment)
            .where(StockAdjustment.branch_id == branch_id)
            .order_by(StockAdjustment.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ═══════════════════════════════════════════════════════════════════════════
    # INVENTORY POLICY  (delegates to SettingsProductService pattern)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_inventory_policy(self) -> InventoryPolicy:
        policy = await self.db.get(InventoryPolicy, "default")
        if not policy:
            policy = InventoryPolicy(id="default", updated_at=datetime.now(UTC).isoformat())
            self.db.add(policy)
            await self.db.commit()
        return policy

    async def is_auto_depletion_enabled(self) -> bool:
        policy = await self.get_inventory_policy()
        return policy.enable_auto_depletion

    # ═══════════════════════════════════════════════════════════════════════════
    # COSTING HELPERS  (used by ReportingService)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_stock_valuation(self, branch_id: int) -> dict:
        """
        Returns total stock value at cost (average cost method).
        For FIFO, batch_number tracking would be used — not implemented here.
        """
        levels = await self.get_stock_levels(branch_id)
        total_value = Decimal("0.00")
        line_items = []

        for level in levels:
            cost = to_money(level.get("cost_price") or 0)
            qty = level["current_stock"]
            line_value = to_money(cost * qty)
            total_value += line_value
            line_items.append({
                **level,
                "cost_price": cost,
                "stock_value": line_value,
            })

        return {
            "branch_id": branch_id,
            "total_stock_value": to_money(total_value),
            "items": line_items,
        }