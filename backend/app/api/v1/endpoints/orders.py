from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.enums import PosOrderStatus
from app.models.user import User
from app.schemas.order import (
    PosOrderClose,
    PosOrderCreate,
    PosOrderItemAdd,
    PosOrderItemUpdate,
    PosOrderItemVoid,
    PosOrderRead,
)
from app.services.order import (
    OrderNotFoundError,
    OrderServiceError,
    create_order,
    add_order_item,
    close_order,
    get_order,
    hold_order,
    list_orders,
    send_order,
    update_order_item,
    void_order,
    void_order_item,
)

router = APIRouter(prefix="/orders", tags=["orders"])
STAFF_ROLES = ["admin", "manager", "cashier", "server"]


@router.get("/", response_model=list[PosOrderRead])
async def get_orders(
    branch_id: int | None = Query(default=None),
    status_filter: PosOrderStatus | None = Query(default=None, alias="status"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> list[PosOrderRead]:
    return await list_orders(
        db,
        branch_id=branch_id,
        status=status_filter,
        active_only=active_only,
    )


@router.post("/", response_model=PosOrderRead, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    payload: PosOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await create_order(db, payload, staff_user_id=current_user.id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=PosOrderRead)
async def get_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await get_order(db, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{order_id}/items", response_model=PosOrderRead)
async def add_order_item_endpoint(
    order_id: int,
    payload: PosOrderItemAdd,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await add_order_item(db, order_id, payload)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{order_id}/items/{item_id}", response_model=PosOrderRead)
async def update_order_item_endpoint(
    order_id: int,
    item_id: int,
    payload: PosOrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await update_order_item(db, order_id, item_id, payload)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/items/{item_id}/void", response_model=PosOrderRead)
async def void_order_item_endpoint(
    order_id: int,
    item_id: int,
    payload: PosOrderItemVoid,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await void_order_item(db, order_id, item_id, payload)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/send", response_model=PosOrderRead)
async def send_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await send_order(db, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/hold", response_model=PosOrderRead)
async def hold_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await hold_order(db, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/void", response_model=PosOrderRead)
async def void_order_endpoint(
    order_id: int,
    payload: PosOrderItemVoid,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await void_order(db, order_id, payload.reason)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{order_id}/close", response_model=PosOrderRead)
async def close_order_endpoint(
    order_id: int,
    payload: PosOrderClose,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(STAFF_ROLES)),
) -> PosOrderRead:
    try:
        return await close_order(db, order_id, payload)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
