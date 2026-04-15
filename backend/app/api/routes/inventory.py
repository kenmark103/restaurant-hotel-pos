"""
routes/inventory.py
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_manager
from app.db.models import User
from app.db.session import get_db
from app.services.inventory_service import InventoryService

router = APIRouter()


def _inv(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> InventoryService:
    return InventoryService(db, user)


@router.get("/stock")
async def get_stock(
    branch_id: int,
    low_stock_only: bool = False,
    _: User = Depends(require_manager),
    svc: InventoryService = Depends(_inv),
):
    return await svc.get_stock_levels(branch_id, low_stock_only=low_stock_only)


@router.get("/low-stock")
async def low_stock_alerts(
    branch_id: int,
    _: User = Depends(require_manager),
    svc: InventoryService = Depends(_inv),
):
    return await svc.get_low_stock_items(branch_id)


@router.post("/adjustments", status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    branch_id: int,
    menu_item_id: int,
    quantity_after: Decimal,
    reason: str,
    variant_id: Optional[int] = None,
    notes: Optional[str] = None,
    _: User = Depends(require_manager),
    svc: InventoryService = Depends(_inv),
):
    return await svc.adjust_stock(
        branch_id=branch_id,
        menu_item_id=menu_item_id,
        quantity_after=quantity_after,
        reason=reason,
        variant_id=variant_id,
        notes=notes,
    )


@router.post("/waste", status_code=status.HTTP_201_CREATED)
async def log_waste(
    branch_id: int,
    menu_item_id: int,
    quantity: Decimal,
    reason: str,
    variant_id: Optional[int] = None,
    _: User = Depends(require_manager),
    svc: InventoryService = Depends(_inv),
):
    return await svc.log_waste(
        branch_id=branch_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        reason=reason,
        variant_id=variant_id,
    )


@router.get("/movements")
async def movement_history(
    branch_id: int,
    menu_item_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_manager),
    svc: InventoryService = Depends(_inv),
):
    return await svc.get_movement_history(branch_id, menu_item_id=menu_item_id, skip=skip, limit=limit)