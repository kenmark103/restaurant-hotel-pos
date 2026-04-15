"""
product_service.py — Menu & Catalogue management
─────────────────────────────────────────────────────────────────────────────
Covers:
  • Hierarchical category tree with drag-drop reordering
  • Menu items with variants, modifiers, stock linkage
  • Barcode / SKU lookup
  • Availability toggling and soft-delete
  • Public (customer-facing) menu endpoint
  • Text search
"""
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    KitchenStation,
    MenuCategory,
    MenuItem,
    MenuItemVariant,
    MenuModifierGroup,
    MenuModifierOption,
    UnitOfMeasure,
)
from app.services.base import (
    BaseService,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class ProductService(BaseService[MenuItem]):
    model = MenuItem

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY TREE
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_category_tree(
        self,
        branch_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[MenuCategory]:
        """Load the full category tree (root → children → grandchildren) in one query."""
        query = (
            select(MenuCategory)
            .options(
                selectinload(MenuCategory.items)
                .selectinload(MenuItem.variants),
                selectinload(MenuCategory.children)
                .selectinload(MenuCategory.items)
                .selectinload(MenuItem.variants),
                selectinload(MenuCategory.children)
                .selectinload(MenuCategory.children),
            )
            .where(MenuCategory.parent_id.is_(None))
            .order_by(MenuCategory.display_order, MenuCategory.name)
        )

        if branch_id is not None:
            query = query.where(
                (MenuCategory.branch_id == branch_id) | (MenuCategory.branch_id.is_(None))
            )
        if active_only:
            query = query.where(MenuCategory.is_active == True)

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def create_category(
        self,
        name: str,
        branch_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        **kwargs,
    ) -> MenuCategory:
        if parent_id:
            parent = await self.db.get(MenuCategory, parent_id)
            if not parent:
                raise NotFoundError("Parent category")

        category = MenuCategory(name=name, branch_id=branch_id, parent_id=parent_id, **kwargs)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update_category(self, category_id: int, **data) -> MenuCategory:
        category = await self.db.get(MenuCategory, category_id)
        if not category:
            raise NotFoundError("Category")

        if "parent_id" in data and data["parent_id"]:
            parent = await self.db.get(MenuCategory, data["parent_id"])
            if not parent:
                raise NotFoundError("Parent category")
            # Prevent self-referential loop
            if data["parent_id"] == category_id:
                raise ValidationError("Category cannot be its own parent")

        for key, value in data.items():
            if value is not None and hasattr(category, key):
                setattr(category, key, value)

        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete_category(self, category_id: int, soft: bool = True) -> None:
        """
        Soft-delete by default (sets is_active=False).
        Hard delete removes the row; child categories are SET NULL (per model FK).
        """
        category = await self.db.get(MenuCategory, category_id)
        if not category:
            raise NotFoundError("Category")

        if soft:
            category.is_active = False
            await self.db.commit()
        else:
            await self.db.delete(category)
            await self.db.commit()

    async def reorder_categories(
        self,
        ordered_ids: List[int],
        parent_id: Optional[int] = None,
    ) -> List[MenuCategory]:
        """Update display_order for drag-drop reordering within a parent."""
        for index, cat_id in enumerate(ordered_ids):
            cat = await self.db.get(MenuCategory, cat_id)
            if not cat:
                raise NotFoundError(f"Category {cat_id}")
            if cat.parent_id != parent_id:
                raise ValidationError(f"Category {cat_id} does not belong to the specified parent")
            cat.display_order = index
        await self.db.commit()
        return await self.get_category_tree()

    # ═══════════════════════════════════════════════════════════════════════════
    # MENU ITEMS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_item_with_relations(self, item_id: int) -> Optional[MenuItem]:
        """Eagerly load item + variants + modifier groups + options + station."""
        result = await self.db.execute(
            select(MenuItem)
            .options(
                selectinload(MenuItem.variants),
                selectinload(MenuItem.modifier_groups).selectinload(MenuModifierGroup.options),
                selectinload(MenuItem.unit_of_measure),
                selectinload(MenuItem.kitchen_station),
                selectinload(MenuItem.category),
            )
            .where(MenuItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def create_menu_item(self, **data) -> MenuItem:
        """
        Create a menu item with optional inline variants and modifier groups.

        ``data`` may contain:
          variants      – list of variant dicts
          modifier_groups – list of modifier group dicts (each with nested options)
        All other keys are applied directly to the MenuItem.
        """
        variants_data = data.pop("variants", [])
        modifiers_data = data.pop("modifier_groups", [])

        # Validate category
        category = await self.db.get(MenuCategory, data.get("category_id"))
        if not category:
            raise NotFoundError("Category")

        # Validate kitchen station if provided
        if data.get("kitchen_station_id"):
            station = await self.db.get(KitchenStation, data["kitchen_station_id"])
            if not station:
                raise NotFoundError("KitchenStation")

        # Validate unit of measure
        if data.get("unit_of_measure_id"):
            unit = await self.db.get(UnitOfMeasure, data["unit_of_measure_id"])
            if not unit:
                raise NotFoundError("UnitOfMeasure")

        item = MenuItem(**data)
        self.db.add(item)
        await self.db.flush()  # get item.id

        # Create variants
        for idx, var_data in enumerate(variants_data):
            variant = MenuItemVariant(menu_item_id=item.id, display_order=idx, **var_data)
            self.db.add(variant)

        # Create modifier groups + options
        for mod_group_data in modifiers_data:
            options = mod_group_data.pop("options", [])
            group = MenuModifierGroup(menu_item_id=item.id, **mod_group_data)
            self.db.add(group)
            await self.db.flush()
            for opt_data in options:
                self.db.add(MenuModifierOption(group_id=group.id, **opt_data))

        await self.db.commit()
        return await self.get_item_with_relations(item.id)

    async def update_menu_item(self, item_id: int, **data) -> MenuItem:
        """
        Partial update.  If ``variants`` is provided it fully replaces existing
        variants (delete-and-recreate).  Modifier groups are unchanged unless
        explicitly managed via the modifier-group endpoints.
        """
        item = await self.get_or_404(item_id)

        # Handle scalar fields
        for key, value in data.items():
            if key in ("variants", "modifier_groups"):
                continue
            if value is not None and hasattr(item, key):
                setattr(item, key, value)

        # Full variant replacement (simpler than diffing)
        if "variants" in data:
            existing = await self.db.execute(
                select(MenuItemVariant).where(MenuItemVariant.menu_item_id == item_id)
            )
            for v in existing.scalars():
                await self.db.delete(v)
            for idx, var_data in enumerate(data["variants"]):
                self.db.add(MenuItemVariant(menu_item_id=item_id, display_order=idx, **var_data))

        await self.db.commit()
        return await self.get_item_with_relations(item_id)

    async def toggle_availability(self, item_id: int) -> MenuItem:
        item = await self.get_or_404(item_id)
        item.is_available = not item.is_available
        await self.db.commit()
        return item

    async def soft_delete_item(self, item_id: int) -> None:
        """Mark item as unavailable instead of hard-deleting (preserves order history)."""
        item = await self.get_or_404(item_id)
        item.is_available = False
        # Soft-delete: we keep the row so historical order snapshots remain valid
        await self.db.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    # MODIFIER GROUPS  (standalone CRUD for post-creation edits)
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_modifier_group(self, item_id: int, **data) -> MenuModifierGroup:
        item = await self.get_or_404(item_id)
        options = data.pop("options", [])
        group = MenuModifierGroup(menu_item_id=item_id, **data)
        self.db.add(group)
        await self.db.flush()
        for opt_data in options:
            self.db.add(MenuModifierOption(group_id=group.id, **opt_data))
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def update_modifier_group(self, group_id: int, **data) -> MenuModifierGroup:
        group = await self.db.get(MenuModifierGroup, group_id)
        if not group:
            raise NotFoundError("ModifierGroup")
        for key, value in data.items():
            if key != "options" and value is not None:
                setattr(group, key, value)
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def delete_modifier_group(self, group_id: int) -> None:
        group = await self.db.get(MenuModifierGroup, group_id)
        if not group:
            raise NotFoundError("ModifierGroup")
        await self.db.delete(group)
        await self.db.commit()

    async def create_modifier_option(self, group_id: int, **data) -> MenuModifierOption:
        group = await self.db.get(MenuModifierGroup, group_id)
        if not group:
            raise NotFoundError("ModifierGroup")
        option = MenuModifierOption(group_id=group_id, **data)
        self.db.add(option)
        await self.db.commit()
        await self.db.refresh(option)
        return option

    async def update_modifier_option(self, option_id: int, **data) -> MenuModifierOption:
        option = await self.db.get(MenuModifierOption, option_id)
        if not option:
            raise NotFoundError("ModifierOption")
        for key, value in data.items():
            if value is not None:
                setattr(option, key, value)
        await self.db.commit()
        await self.db.refresh(option)
        return option

    async def delete_modifier_option(self, option_id: int) -> None:
        option = await self.db.get(MenuModifierOption, option_id)
        if not option:
            raise NotFoundError("ModifierOption")
        await self.db.delete(option)
        await self.db.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    # LOOKUP
    # ═══════════════════════════════════════════════════════════════════════════

    async def lookup_by_barcode(self, barcode: str) -> Optional[MenuItem]:
        """Used by POS barcode scanner — checks item barcode then variant barcode."""
        result = await self.db.execute(select(MenuItem).where(MenuItem.barcode == barcode))
        item = result.scalar_one_or_none()
        if item:
            return await self.get_item_with_relations(item.id)

        result = await self.db.execute(
            select(MenuItemVariant).where(MenuItemVariant.barcode == barcode)
        )
        variant = result.scalar_one_or_none()
        if variant:
            return await self.get_item_with_relations(variant.menu_item_id)

        return None

    async def search_items(
        self,
        query_str: str,
        branch_id: Optional[int] = None,
        active_only: bool = True,
        limit: int = 30,
    ) -> List[MenuItem]:
        """
        Full text search across item name, description, SKU and barcode.
        Useful for the POS quick-search bar.
        """
        term = f"%{query_str.strip()}%"
        query = (
            select(MenuItem)
            .options(selectinload(MenuItem.variants))
            .where(
                or_(
                    MenuItem.name.ilike(term),
                    MenuItem.description.ilike(term),
                    MenuItem.sku.ilike(term),
                    MenuItem.barcode.ilike(term),
                )
            )
            .limit(limit)
        )
        if active_only:
            query = query.where(MenuItem.is_available == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC MENU  (customer-facing — available items only)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_public_menu(self, branch_id: Optional[int] = None) -> List[MenuCategory]:
        """
        Returns the menu tree filtered to active categories and available items.
        Used by customer-facing display, QR menu, and online ordering.
        Also respects time-based availability (available_from / available_until).
        """
        from datetime import datetime, timezone

        now_time = datetime.now(timezone.utc).strftime("%H:%M")

        query = (
            select(MenuCategory)
            .options(
                selectinload(MenuCategory.items)
                .selectinload(MenuItem.variants),
                selectinload(MenuCategory.items)
                .selectinload(MenuItem.modifier_groups)
                .selectinload(MenuModifierGroup.options),
                selectinload(MenuCategory.children)
                .selectinload(MenuCategory.items)
                .selectinload(MenuItem.variants),
            )
            .where(
                MenuCategory.parent_id.is_(None),
                MenuCategory.is_active == True,
            )
            .order_by(MenuCategory.display_order)
        )

        if branch_id is not None:
            query = query.where(
                (MenuCategory.branch_id == branch_id) | (MenuCategory.branch_id.is_(None))
            )

        result = await self.db.execute(query)
        categories = list(result.scalars().unique().all())

        # Filter items to available only
        for cat in categories:
            cat.items = [i for i in cat.items if i.is_available]
            for child in cat.children:
                child.items = [i for i in child.items if i.is_available]

        return categories

    # ═══════════════════════════════════════════════════════════════════════════
    # KITCHEN STATIONS  (read-only shortcut — configuration managed by SettingsProductService)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_kitchen_stations(self, active_only: bool = True) -> List[KitchenStation]:
        query = select(KitchenStation).order_by(KitchenStation.print_order)
        if active_only:
            query = query.where(KitchenStation.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())