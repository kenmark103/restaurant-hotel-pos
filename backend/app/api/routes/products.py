"""
routes/products.py — Menu catalogue endpoints
─────────────────────────────────────────────────────────────────────────────
Prefix: /products
Covers categories, menu items, variants, modifiers, barcode lookup, search,
and the public QR menu.

NOTE: Units of measure, kitchen stations, inventory policy, and tax templates
are NOT here — they live at /settings/product (routes/settings_product.py).
The product_service.get_kitchen_stations() convenience read is exposed as
GET /products/stations for POS item-creation forms only.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_optional_user, require_manager
from app.db.models import User
from app.db.session import get_db
from app.schemas.products import (
    CategoryCreate,
    CategoryRead,
    CategoryReorderPayload,
    CategoryUpdate,
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    ModifierGroupCreate,
    ModifierGroupRead,
    ModifierGroupUpdate,
    ModifierOptionCreate,
    ModifierOptionRead,
    ModifierOptionUpdate,
)
from app.services.product_service import ProductService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> ProductService:
    return ProductService(db, user)


# ─────────────────────────────────────────────────────────────────────────────
# Public menu  (no auth — customer QR scan)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/public-menu", response_model=list[CategoryRead])
async def public_menu(
    branch_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    svc = ProductService(db)
    return await svc.get_public_menu(branch_id=branch_id)


# ─────────────────────────────────────────────────────────────────────────────
# Kitchen stations (read-only convenience for item-creation forms)
# Full CRUD lives at /settings/product/stations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stations")
async def list_stations_for_items(
    active_only: bool = True,
    svc: ProductService = Depends(_svc),
):
    """Read-only list of stations — used when assigning a station to a menu item."""
    return await svc.get_kitchen_stations(active_only=active_only)


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryRead])
async def get_category_tree(
    branch_id: Optional[int] = None,
    active_only: bool = True,
    _: User = Depends(get_current_user),
    svc: ProductService = Depends(_svc),
):
    return await svc.get_category_tree(branch_id=branch_id, active_only=active_only)


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.create_category(
        name=payload.name,
        branch_id=payload.branch_id,
        parent_id=payload.parent_id,
        description=payload.description,
        image_url=payload.image_url,
        display_order=payload.display_order,
        color_code=payload.color_code,
        available_from=payload.available_from,
        available_until=payload.available_until,
    )


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.update_category(
        category_id, **payload.model_dump(exclude_unset=True)
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    soft: bool = True,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    await svc.delete_category(category_id, soft=soft)


@router.post("/categories/reorder", response_model=list[CategoryRead])
async def reorder_categories(
    payload: CategoryReorderPayload,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.reorder_categories(payload.ordered_ids, parent_id=payload.parent_id)


# ─────────────────────────────────────────────────────────────────────────────
# Menu items
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/items/search", response_model=list[MenuItemRead])
async def search_items(
    q: str = Query(min_length=1),
    branch_id: Optional[int] = None,
    active_only: bool = True,
    limit: int = Query(default=30, le=100),
    _: User = Depends(get_current_user),
    svc: ProductService = Depends(_svc),
):
    return await svc.search_items(q, branch_id=branch_id, active_only=active_only, limit=limit)


@router.get("/items/barcode/{barcode}", response_model=Optional[MenuItemRead])
async def lookup_by_barcode(
    barcode: str,
    _: User = Depends(get_current_user),
    svc: ProductService = Depends(_svc),
):
    return await svc.lookup_by_barcode(barcode)


@router.get("/items/{item_id}", response_model=MenuItemRead)
async def get_item(
    item_id: int,
    _: User = Depends(get_current_user),
    svc: ProductService = Depends(_svc),
):
    item = await svc.get_item_with_relations(item_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="MenuItem not found")
    return item


@router.post("/items", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: MenuItemCreate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.create_menu_item(**payload.model_dump())


@router.patch("/items/{item_id}", response_model=MenuItemRead)
async def update_item(
    item_id: int,
    payload: MenuItemUpdate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.update_menu_item(item_id, **payload.model_dump(exclude_unset=True))


@router.patch("/items/{item_id}/availability", response_model=MenuItemRead)
async def toggle_availability(
    item_id: int,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.toggle_availability(item_id)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    await svc.soft_delete_item(item_id)


# ─────────────────────────────────────────────────────────────────────────────
# Modifier groups
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/items/{item_id}/modifier-groups",
    response_model=ModifierGroupRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_modifier_group(
    item_id: int,
    payload: ModifierGroupCreate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.create_modifier_group(item_id, **payload.model_dump())


@router.patch("/modifier-groups/{group_id}", response_model=ModifierGroupRead)
async def update_modifier_group(
    group_id: int,
    payload: ModifierGroupUpdate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.update_modifier_group(group_id, **payload.model_dump(exclude_unset=True))


@router.delete("/modifier-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modifier_group(
    group_id: int,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    await svc.delete_modifier_group(group_id)


# ─────────────────────────────────────────────────────────────────────────────
# Modifier options
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/modifier-groups/{group_id}/options",
    response_model=ModifierOptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_modifier_option(
    group_id: int,
    payload: ModifierOptionCreate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.create_modifier_option(group_id, **payload.model_dump())


@router.patch("/modifier-options/{option_id}", response_model=ModifierOptionRead)
async def update_modifier_option(
    option_id: int,
    payload: ModifierOptionUpdate,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    return await svc.update_modifier_option(option_id, **payload.model_dump(exclude_unset=True))


@router.delete("/modifier-options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modifier_option(
    option_id: int,
    _: User = Depends(require_manager),
    svc: ProductService = Depends(_svc),
):
    await svc.delete_modifier_option(option_id)