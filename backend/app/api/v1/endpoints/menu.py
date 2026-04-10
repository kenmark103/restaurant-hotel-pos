from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.menu import (
    CategoryCreate,
    MenuCategoryRead,
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    VariantCreate,
    VariantRead,
    VariantUpdate,
)
from app.services.menu import (
    MenuNotFoundError,
    add_variant,
    create_category,
    create_menu_item,
    delete_variant,
    list_categories,
    update_menu_item,
    update_variant,
)

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/", response_model=list[MenuCategoryRead])
async def get_menu_categories(
    branch_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[MenuCategoryRead]:
    return await list_categories(db, branch_id=branch_id, top_level_only=True)


@router.post("/categories", response_model=MenuCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> MenuCategoryRead:
    try:
        return await create_category(db, payload)
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/items", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
async def create_menu_item_endpoint(
    payload: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> MenuItemRead:
    return await create_menu_item(db, payload)


@router.patch("/items/{item_id}", response_model=MenuItemRead)
async def update_menu_item_endpoint(
    item_id: int,
    payload: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> MenuItemRead:
    try:
        return await update_menu_item(db, item_id, payload)
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/items/{item_id}/variants", response_model=VariantRead, status_code=status.HTTP_201_CREATED)
async def add_variant_endpoint(
    item_id: int,
    payload: VariantCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> VariantRead:
    try:
        return await add_variant(db, item_id, payload)
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/variants/{variant_id}", response_model=VariantRead)
async def update_variant_endpoint(
    variant_id: int,
    payload: VariantUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> VariantRead:
    try:
        return await update_variant(db, variant_id, payload)
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant_endpoint(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> None:
    try:
        await delete_variant(db, variant_id)
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
