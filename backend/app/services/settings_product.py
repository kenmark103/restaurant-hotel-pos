"""
settings_product.py — Product configuration management
─────────────────────────────────────────────────────────────────────────────
Manages the catalogue-level configuration that must exist before menu items
can be created:
  • UnitOfMeasure   – piece / kg / litre / etc.
  • KitchenStation  – grill / bar / fryer / etc.
  • InventoryPolicy – global depletion / alert rules
  • TaxTemplate     – reusable tax rules
"""
import json
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InventoryPolicy, KitchenStation, TaxTemplate, UnitOfMeasure
from app.services.base import ConflictError, NotFoundError, ValidationError


class SettingsProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ═══════════════════════════════════════════════════════════════════════════
    # UNITS OF MEASURE
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_units(self, active_only: bool = False) -> list[UnitOfMeasure]:
        query = select(UnitOfMeasure).order_by(UnitOfMeasure.sort_order, UnitOfMeasure.name)
        if active_only:
            query = query.where(UnitOfMeasure.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unit(self, unit_id: str) -> UnitOfMeasure:
        unit = await self.db.get(UnitOfMeasure, unit_id)
        if not unit:
            raise NotFoundError("UnitOfMeasure")
        return unit

    async def create_unit(self, data: dict) -> UnitOfMeasure:
        existing = await self.db.get(UnitOfMeasure, data["id"])
        if existing:
            raise ConflictError(f"Unit ID '{data['id']}' already exists")
        unit = UnitOfMeasure(**data)
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def update_unit(self, unit_id: str, data: dict) -> UnitOfMeasure:
        unit = await self.get_unit(unit_id)
        for field, value in data.items():
            if value is not None and hasattr(unit, field):
                setattr(unit, field, value)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def delete_unit(self, unit_id: str) -> None:
        unit = await self.get_unit(unit_id)
        # Soft-check: prevent deletion if any menu items reference this unit
        from app.db.models import MenuItem
        in_use = await self.db.scalar(
            select(MenuItem).where(MenuItem.unit_of_measure_id == unit_id).limit(1)
        )
        if in_use:
            raise ValidationError("Unit is in use by menu items; deactivate instead of deleting.")
        await self.db.delete(unit)
        await self.db.commit()

    async def reorder_units(self, ordered_ids: list[str]) -> list[UnitOfMeasure]:
        for index, unit_id in enumerate(ordered_ids):
            unit = await self.db.get(UnitOfMeasure, unit_id)
            if unit:
                unit.sort_order = index
        await self.db.commit()
        return await self.get_units()

    # ═══════════════════════════════════════════════════════════════════════════
    # KITCHEN STATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_stations(self, active_only: bool = False) -> list[KitchenStation]:
        query = select(KitchenStation).order_by(KitchenStation.print_order)
        if active_only:
            query = query.where(KitchenStation.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_station(self, station_id: str) -> KitchenStation:
        station = await self.db.get(KitchenStation, station_id)
        if not station:
            raise NotFoundError("KitchenStation")
        return station

    async def create_station(self, data: dict) -> KitchenStation:
        existing = await self.db.get(KitchenStation, data["id"])
        if existing:
            raise ConflictError(f"Station ID '{data['id']}' already exists")
        station = KitchenStation(**data)
        self.db.add(station)
        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def update_station(self, station_id: str, data: dict) -> KitchenStation:
        station = await self.get_station(station_id)
        for field, value in data.items():
            if value is not None and hasattr(station, field):
                setattr(station, field, value)
        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def delete_station(self, station_id: str) -> None:
        station = await self.get_station(station_id)
        # Prevent deletion if menu items are routed here
        from app.db.models import MenuItem
        in_use = await self.db.scalar(
            select(MenuItem).where(MenuItem.kitchen_station_id == station_id).limit(1)
        )
        if in_use:
            raise ValidationError("Station has menu items assigned; deactivate instead.")
        await self.db.delete(station)
        await self.db.commit()

    async def reorder_stations(self, ordered_ids: list[str]) -> list[KitchenStation]:
        for index, station_id in enumerate(ordered_ids):
            station = await self.db.get(KitchenStation, station_id)
            if station:
                station.print_order = index + 1  # 1-based for print ordering
        await self.db.commit()
        return await self.get_stations()

    # ═══════════════════════════════════════════════════════════════════════════
    # INVENTORY POLICY  (singleton)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_inventory_policy(self) -> InventoryPolicy:
        policy = await self.db.get(InventoryPolicy, "default")
        if not policy:
            policy = InventoryPolicy(id="default", updated_at=datetime.now(UTC).isoformat())
            self.db.add(policy)
            await self.db.commit()
            await self.db.refresh(policy)
        return policy

    async def update_inventory_policy(self, data: dict) -> InventoryPolicy:
        policy = await self.get_inventory_policy()
        for field, value in data.items():
            if value is None or not hasattr(policy, field):
                continue
            # alert_recipients is stored as a JSON string
            if field == "alert_recipients" and isinstance(value, list):
                setattr(policy, field, json.dumps(value))
            else:
                setattr(policy, field, value)
        policy.updated_at = datetime.now(UTC).isoformat()
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    # ═══════════════════════════════════════════════════════════════════════════
    # TAX TEMPLATES
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_tax_templates(self, active_only: bool = False) -> list[TaxTemplate]:
        query = select(TaxTemplate).order_by(TaxTemplate.created_at)
        if active_only:
            query = query.where(TaxTemplate.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tax_template(self, tax_id: str) -> TaxTemplate:
        tax = await self.db.get(TaxTemplate, tax_id)
        if not tax:
            raise NotFoundError("TaxTemplate")
        return tax

    async def create_tax_template(self, data: dict) -> TaxTemplate:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "target_ids" in data and isinstance(data["target_ids"], list):
            data["target_ids"] = json.dumps(data["target_ids"])
        if data.get("is_default"):
            await self._unset_default_taxes()
        tax = TaxTemplate(**data)
        self.db.add(tax)
        await self.db.commit()
        await self.db.refresh(tax)
        return tax

    async def update_tax_template(self, tax_id: str, data: dict) -> TaxTemplate:
        tax = await self.get_tax_template(tax_id)
        if "target_ids" in data and isinstance(data["target_ids"], list):
            data["target_ids"] = json.dumps(data["target_ids"])
        if data.get("is_default") and not tax.is_default:
            await self._unset_default_taxes()
        for field, value in data.items():
            if value is not None and hasattr(tax, field):
                setattr(tax, field, value)
        await self.db.commit()
        await self.db.refresh(tax)
        return tax

    async def delete_tax_template(self, tax_id: str) -> None:
        tax = await self.get_tax_template(tax_id)
        await self.db.delete(tax)
        await self.db.commit()

    async def set_default_tax(self, tax_id: str) -> list[TaxTemplate]:
        tax = await self.get_tax_template(tax_id)
        await self._unset_default_taxes()
        tax.is_default = True
        await self.db.commit()
        return await self.get_tax_templates()

    async def _unset_default_taxes(self) -> None:
        result = await self.db.execute(select(TaxTemplate).where(TaxTemplate.is_default == True))
        for t in result.scalars():
            t.is_default = False

    # ═══════════════════════════════════════════════════════════════════════════
    # BULK FETCH  (single round-trip for initial app load)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_configuration(self) -> dict:
        """Return all product configuration in one DB round-trip set."""
        units = await self.get_units()
        stations = await self.get_stations()
        policy = await self.get_inventory_policy()
        taxes = await self.get_tax_templates()
        return {
            "units": units,
            "stations": stations,
            "inventory_policy": policy,
            "tax_templates": taxes,
        }