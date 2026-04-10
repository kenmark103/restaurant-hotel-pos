"""
app/services/menu.py  — replace existing file with this version.
Adds: variant CRUD, subcategory-aware list, barcode lookup, stock level query.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu_category import MenuCategory
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.stock_movement import StockMovement
from app.schemas.menu import (
    CategoryCreate,
    MenuItemCreate,
    MenuItemUpdate,
    StockLevelRead,
    VariantCreate,
    VariantUpdate,
)


class MenuServiceError(Exception):
    pass


class MenuNotFoundError(MenuServiceError):
    pass


# ─── item loader helper ────────────────────────────────────────────────────────

def _item_query():
    return select(MenuItem).options(
        selectinload(MenuItem.variants),
        selectinload(MenuItem.modifier_groups),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

async def list_categories(
    db: AsyncSession,
    branch_id: int | None = None,
    top_level_only: bool = False,
) -> list[MenuCategory]:
    """
    Returns categories with their children and items eagerly loaded.
    If top_level_only=True, returns only root categories (parent_id IS NULL).
    Subcategories are accessible via category.children.
    """
    children_loader = selectinload(MenuCategory.children)
    stmt = (
        select(MenuCategory)
        .options(
            selectinload(MenuCategory.items).selectinload(MenuItem.variants),
            children_loader.selectinload(MenuCategory.items).selectinload(MenuItem.variants),
            children_loader.selectinload(MenuCategory.children),
            children_loader.selectinload(MenuCategory.children)
            .selectinload(MenuCategory.items)
            .selectinload(MenuItem.variants),
        )
        .order_by(MenuCategory.display_order.asc(), MenuCategory.name.asc())
    )

    if branch_id is not None:
        stmt = stmt.where(
            (MenuCategory.branch_id == branch_id) | (MenuCategory.branch_id.is_(None))
        )

    if top_level_only:
        stmt = stmt.where(MenuCategory.parent_id.is_(None))

    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def create_category(db: AsyncSession, payload: CategoryCreate) -> MenuCategory:
    if payload.parent_id is not None:
        parent = await db.get(MenuCategory, payload.parent_id)
        if parent is None:
            raise MenuNotFoundError("Parent category not found.")

    category = MenuCategory(
        branch_id=payload.branch_id,
        parent_id=payload.parent_id,
        name=payload.name,
        description=payload.description,
        display_order=payload.display_order,
        available_from=payload.available_from,
        available_until=payload.available_until,
    )
    db.add(category)
    await db.commit()

    children_loader = selectinload(MenuCategory.children)
    result = await db.execute(
        select(MenuCategory)
        .options(
            selectinload(MenuCategory.items).selectinload(MenuItem.variants),
            children_loader.selectinload(MenuCategory.items).selectinload(MenuItem.variants),
            children_loader.selectinload(MenuCategory.children),
            children_loader.selectinload(MenuCategory.children)
            .selectinload(MenuCategory.items)
            .selectinload(MenuItem.variants),
        )
        .where(MenuCategory.id == category.id)
    )
    return result.scalar_one()


# ═══════════════════════════════════════════════════════════════════════════════
# MENU ITEMS
# ═══════════════════════════════════════════════════════════════════════════════

async def create_menu_item(db: AsyncSession, payload: MenuItemCreate) -> MenuItem:
    item = MenuItem(
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        base_price=payload.base_price,
        cost_price=payload.cost_price,
        image_url=payload.image_url,
        sku=payload.sku,
        barcode=payload.barcode,
        unit_of_measure=payload.unit_of_measure,
        track_inventory=payload.track_inventory,
        low_stock_threshold=payload.low_stock_threshold,
        is_available=payload.is_available,
        prep_time_minutes=payload.prep_time_minutes,
        station=payload.station,
    )
    db.add(item)
    await db.flush()  # get item.id

    for v in payload.variants:
        db.add(MenuItemVariant(
            menu_item_id=item.id,
            name=v.name,
            sell_price=v.sell_price,
            cost_price=v.cost_price,
            barcode=v.barcode,
            sku=v.sku,
            display_order=v.display_order,
            is_default=v.is_default,
        ))

    await db.commit()

    result = await db.execute(_item_query().where(MenuItem.id == item.id))
    return result.scalar_one()


async def update_menu_item(
    db: AsyncSession, item_id: int, payload: MenuItemUpdate
) -> MenuItem:
    result = await db.execute(_item_query().where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise MenuNotFoundError("Menu item not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


async def get_item_by_barcode(db: AsyncSession, barcode: str) -> MenuItem | None:
    """
    Looks up an item by barcode on the item itself or any of its variants.
    Used by the POS barcode scanner.
    Returns the MenuItem (with variants loaded) or None.
    """
    # check item-level barcode
    result = await db.execute(_item_query().where(MenuItem.barcode == barcode))
    item = result.scalar_one_or_none()
    if item:
        return item

    # check variant-level barcode
    variant_result = await db.execute(
        select(MenuItemVariant)
        .options(selectinload(MenuItemVariant.menu_item))
        .where(MenuItemVariant.barcode == barcode)
    )
    variant = variant_result.scalar_one_or_none()
    if variant:
        result = await db.execute(_item_query().where(MenuItem.id == variant.menu_item_id))
        return result.scalar_one_or_none()

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# VARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

async def add_variant(
    db: AsyncSession, item_id: int, payload: VariantCreate
) -> MenuItemVariant:
    item = await db.get(MenuItem, item_id)
    if item is None:
        raise MenuNotFoundError("Menu item not found.")

    variant = MenuItemVariant(
        menu_item_id=item_id,
        name=payload.name,
        sell_price=payload.sell_price,
        cost_price=payload.cost_price,
        barcode=payload.barcode,
        sku=payload.sku,
        display_order=payload.display_order,
        is_default=payload.is_default,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant


async def update_variant(
    db: AsyncSession, variant_id: int, payload: VariantUpdate
) -> MenuItemVariant:
    variant = await db.get(MenuItemVariant, variant_id)
    if variant is None:
        raise MenuNotFoundError("Variant not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)

    await db.commit()
    await db.refresh(variant)
    return variant


async def delete_variant(db: AsyncSession, variant_id: int) -> None:
    variant = await db.get(MenuItemVariant, variant_id)
    if variant is None:
        raise MenuNotFoundError("Variant not found.")
    await db.delete(variant)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# STOCK LEVELS
# ═══════════════════════════════════════════════════════════════════════════════

async def get_stock_levels(
    db: AsyncSession, branch_id: int
) -> list[StockLevelRead]:
    """
    Returns current stock for all tracked items in a branch.
    current_stock = SUM(quantity) from stock_movements.
    Only returns items where track_inventory = True.
    """
    stmt = (
        select(
            StockMovement.menu_item_id,
            StockMovement.variant_id,
            func.sum(StockMovement.quantity).label("current_stock"),
        )
        .where(StockMovement.branch_id == branch_id)
        .group_by(StockMovement.menu_item_id, StockMovement.variant_id)
    )
    rows = (await db.execute(stmt)).all()

    # load item names
    item_ids = list({r.menu_item_id for r in rows})
    items_result = await db.execute(
        select(MenuItem).options(selectinload(MenuItem.variants)).where(MenuItem.id.in_(item_ids))
    )
    items = {item.id: item for item in items_result.scalars().all()}

    levels: list[StockLevelRead] = []
    for row in rows:
        item = items.get(row.menu_item_id)
        if item is None or not item.track_inventory:
            continue

        variant = next((v for v in item.variants if v.id == row.variant_id), None)
        threshold = item.low_stock_threshold
        current = Decimal(str(row.current_stock))

        levels.append(StockLevelRead(
            menu_item_id=item.id,
            variant_id=row.variant_id,
            name=item.name,
            variant_name=variant.name if variant else None,
            current_stock=current,
            unit_of_measure=item.unit_of_measure,
            low_stock_threshold=threshold,
            is_low=threshold is not None and current <= threshold,
        ))

    return sorted(levels, key=lambda x: (x.name, x.variant_name or ""))
