"""
routes/pos.py — POS endpoints
─────────────────────────────────────────────────────────────────────────────
All mutating endpoints use Pydantic request body schemas (no raw query params
on POST/PATCH/DELETE).  GET endpoints use query params as designed.

Sections:
  • Orders   — full lifecycle
  • Tables   — CRUD + floor status
  • Reservations
  • Cash sessions
  • Manager override  (blueprint §4.4)
  • Bulk offline sync (frontend blueprint §7)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_cashier, require_manager, require_server
from app.core.event_bus import bus
from app.core.websocket_manager import websocket_manager
from app.db.models import OrderType, OverrideAction, PosOrderStatus, TableStatus, User
from app.db.session import get_db
from app.schemas.orders import (
    AddOrderItemRequest,
    ApplyDiscountRequest,
    CloseOrderRequest,
    CreateOrderRequest,
    OrderRead,
    SendToKitchenRequest,
    UpdateQuantityRequest,
    VoidItemRequest,
    VoidOrderRequest,
)
from app.services.cash_service import CashService
from app.services.pos_service import POSService
from app.services.table_service import TableService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request body schemas for endpoints that had raw query params
# ─────────────────────────────────────────────────────────────────────────────

class CreateTableRequest(BaseModel):
    branch_id: int
    table_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(default=4, ge=1, le=50)
    floor_zone: Optional[str] = Field(default=None, max_length=50)
    position_x: Optional[int] = None
    position_y: Optional[int] = None


class UpdateTableStatusRequest(BaseModel):
    status: TableStatus


class CreateReservationRequest(BaseModel):
    table_id: int
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: Optional[str] = Field(default=None, max_length=32)
    party_size: int = Field(ge=1)
    reservation_time: datetime
    duration_minutes: int = Field(default=120, ge=15)
    special_requests: Optional[str] = Field(default=None, max_length=500)


class UpdateReservationStatusRequest(BaseModel):
    status: str = Field(description="confirmed | seated | cancelled | no_show")


class OpenSessionRequest(BaseModel):
    branch_id: int
    opening_float: Decimal = Field(ge=0)


class CloseSessionRequest(BaseModel):
    closing_float: Decimal = Field(ge=0)
    closure_notes: Optional[str] = Field(default=None, max_length=1000)


class CashTransactionRequest(BaseModel):
    transaction_type: str = Field(description="paid_out | safe_drop")
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=1, max_length=255)


class MergeTablesRequest(BaseModel):
    primary_table_id: int
    secondary_table_id: int


class SplitBillRequest(BaseModel):
    splits: list[dict] = Field(
        description='[{"item_ids": [1,2], "customer_name": "Alice"}, ...]',
        min_length=1,
    )


class ManagerOverrideRequest(BaseModel):
    branch_id: int
    action: OverrideAction
    manager_pin: str = Field(min_length=5, max_length=5, pattern=r"^\d{5}$")
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    reason: Optional[str] = Field(default=None, max_length=255)


class BulkSyncRequest(BaseModel):
    orders: list[dict] = Field(
        min_length=1,
        description="List of offline orders with optional items[] and client_id",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Service factories
# ─────────────────────────────────────────────────────────────────────────────

def _pos(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> POSService:
    return POSService(db, user, websocket_manager=websocket_manager, event_bus=bus)


def _tables(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> TableService:
    return TableService(db, user, websocket_manager=websocket_manager)


def _cash(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> CashService:
    return CashService(db, user)


# ─────────────────────────────────────────────────────────────────────────────
# Orders
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.create_order(
        order_type=payload.order_type,
        staff_user_id=current_user.id,
        branch_id=payload.branch_id,
        table_id=payload.table_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        room_number=payload.room_number,
        note=payload.note,
    )


@router.get("/orders", response_model=list[OrderRead])
async def list_orders(
    branch_id: int,
    order_status: Optional[PosOrderStatus] = None,
    order_type: Optional[OrderType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.get_orders(
        branch_id=branch_id, status=order_status,
        order_type=order_type, skip=skip, limit=limit,
    )


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.get_order_with_items(order_id)


@router.post("/orders/{order_id}/items", response_model=OrderRead)
async def add_item(
    order_id: int,
    payload: AddOrderItemRequest,
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.add_item(
        order_id=order_id,
        menu_item_id=payload.menu_item_id,
        quantity=payload.quantity,
        variant_id=payload.variant_id,
        modifier_option_ids=payload.modifier_option_ids,
        note=payload.note,
    )


@router.patch("/orders/{order_id}/items/{item_id}/quantity", response_model=OrderRead)
async def update_quantity(
    order_id: int,
    item_id: int,
    payload: UpdateQuantityRequest,
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.update_item_quantity(order_id, item_id, payload.quantity)


@router.delete("/orders/{order_id}/items/{item_id}", response_model=OrderRead)
async def remove_item(
    order_id: int,
    item_id: int,
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.remove_item(order_id, item_id)


@router.post("/orders/{order_id}/items/{item_id}/void", response_model=OrderRead)
async def void_item(
    order_id: int,
    item_id: int,
    payload: VoidItemRequest,
    _: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    return await svc.void_item(order_id, item_id, payload.reason)


@router.post("/orders/{order_id}/void", response_model=OrderRead)
async def void_order(
    order_id: int,
    payload: VoidOrderRequest,
    _: User = Depends(require_manager),
    svc: POSService = Depends(_pos),
):
    return await svc.void_order(order_id, payload.reason)


@router.post("/orders/{order_id}/send", response_model=OrderRead)
async def send_to_kitchen(
    order_id: int,
    payload: SendToKitchenRequest,
    _: User = Depends(require_server),
    svc: POSService = Depends(_pos),
):
    return await svc.send_to_kitchen(order_id, station_filter=payload.station_filter)


@router.post("/orders/{order_id}/close", response_model=OrderRead)
async def close_order(
    order_id: int,
    payload: CloseOrderRequest,
    _: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    return await svc.close_order(
        order_id=order_id,
        payment_method=payload.payment_method,
        amount_paid=payload.amount_paid,
        split_payments=(
            [{"method": p.method.value, "amount": str(p.amount), "reference": p.reference}
             for p in payload.split_payments]
            if payload.split_payments else None
        ),
    )


@router.post("/orders/{order_id}/discounts", response_model=OrderRead)
async def apply_discount(
    order_id: int,
    payload: ApplyDiscountRequest,
    _: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    return await svc.apply_discount(
        order_id=order_id,
        discount_type=payload.discount_type,
        value=payload.value,
        order_item_id=payload.order_item_id,
        reason=payload.reason,
    )


@router.delete("/orders/{order_id}/discounts/{discount_id}", response_model=OrderRead)
async def remove_discount(
    order_id: int,
    discount_id: int,
    _: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    return await svc.remove_discount(order_id, discount_id)


@router.post("/orders/{order_id}/split", response_model=list[OrderRead])
async def split_bill(
    order_id: int,
    payload: SplitBillRequest,
    _: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    return await svc.split_bill(order_id, payload.splits)


@router.post("/orders/merge-tables", response_model=OrderRead)
async def merge_tables(
    payload: MergeTablesRequest,
    _: User = Depends(require_manager),
    svc: POSService = Depends(_pos),
):
    return await svc.merge_tables(payload.primary_table_id, payload.secondary_table_id)


# ─────────────────────────────────────────────────────────────────────────────
# Manager override  (blueprint §4.4)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/override/request", status_code=status.HTTP_201_CREATED)
async def request_manager_override(
    payload: ManagerOverrideRequest,
    current_user: User = Depends(require_cashier),
    svc: POSService = Depends(_pos),
):
    """
    A cashier/server requests a manager override for a privileged action.
    The manager enters their PIN on the same terminal.
    Returns a grant_id valid for 2 minutes.
    """
    grant = await svc.request_manager_override(
        branch_id=payload.branch_id,
        action=payload.action.value,
        manager_pin=payload.manager_pin,
        requesting_user_id=current_user.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        reason=payload.reason,
    )
    return {
        "grant_id": grant.id,
        "action": grant.action,
        "expires_at": grant.expires_at.isoformat(),
        "granted_by_id": grant.granted_by_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bulk offline sync  (frontend blueprint §7)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/orders/bulk-sync")
async def bulk_sync_offline_orders(
    payload: BulkSyncRequest,
    _: User = Depends(get_current_user),
    svc: POSService = Depends(_pos),
):
    """
    Drain the client's offline queue.  Each order may contain an optional
    client_id (cuid2) so the frontend can map temporary IDs to real server IDs.
    Returns [{client_id, order_id, status, error?}] for each submitted order.
    """
    return await svc.bulk_sync_offline_orders(payload.orders)


# ─────────────────────────────────────────────────────────────────────────────
# Tables
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tables")
async def list_tables(
    branch_id: int,
    table_status: Optional[TableStatus] = None,
    floor_zone: Optional[str] = None,
    _: User = Depends(require_server),
    svc: TableService = Depends(_tables),
):
    return await svc.get_tables(branch_id, status=table_status, floor_zone=floor_zone)


@router.post("/tables", status_code=status.HTTP_201_CREATED)
async def create_table(
    payload: CreateTableRequest,
    _: User = Depends(require_manager),
    svc: TableService = Depends(_tables),
):
    return await svc.create_table(
        branch_id=payload.branch_id,
        table_number=payload.table_number,
        capacity=payload.capacity,
        floor_zone=payload.floor_zone,
        position_x=payload.position_x,
        position_y=payload.position_y,
    )


@router.patch("/tables/{table_id}")
async def update_table(
    table_id: int,
    payload: CreateTableRequest,
    _: User = Depends(require_manager),
    svc: TableService = Depends(_tables),
):
    return await svc.update_table(
        table_id,
        table_number=payload.table_number,
        capacity=payload.capacity,
        floor_zone=payload.floor_zone,
        position_x=payload.position_x,
        position_y=payload.position_y,
    )


@router.patch("/tables/{table_id}/status")
async def set_table_status(
    table_id: int,
    payload: UpdateTableStatusRequest,
    _: User = Depends(require_server),
    svc: TableService = Depends(_tables),
):
    return await svc.update_table_status(table_id, payload.status)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: int,
    _: User = Depends(require_manager),
    svc: TableService = Depends(_tables),
):
    await svc.delete_table(table_id)


# ─────────────────────────────────────────────────────────────────────────────
# Reservations
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/reservations")
async def list_reservations(
    branch_id: int,
    res_status: Optional[str] = None,
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    _: User = Depends(require_server),
    svc: TableService = Depends(_tables),
):
    dt = datetime.fromisoformat(date) if date else None
    return await svc.get_reservations(branch_id, date=dt, status=res_status)


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
async def create_reservation(
    payload: CreateReservationRequest,
    _: User = Depends(require_server),
    svc: TableService = Depends(_tables),
):
    return await svc.create_reservation(
        table_id=payload.table_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        party_size=payload.party_size,
        reservation_time=payload.reservation_time,
        duration_minutes=payload.duration_minutes,
        special_requests=payload.special_requests,
    )


@router.patch("/reservations/{reservation_id}/status")
async def update_reservation_status(
    reservation_id: int,
    payload: UpdateReservationStatusRequest,
    _: User = Depends(require_server),
    svc: TableService = Depends(_tables),
):
    return await svc.update_reservation_status(reservation_id, payload.status)


# ─────────────────────────────────────────────────────────────────────────────
# Cash sessions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sessions/current")
async def get_current_session(
    branch_id: int,
    _: User = Depends(require_cashier),
    svc: CashService = Depends(_cash),
):
    session = await svc.get_current_session(branch_id)
    return session if session else {"open": False}


@router.get("/sessions")
async def list_sessions(
    branch_id: int,
    limit: int = Query(default=30, le=100),
    _: User = Depends(require_manager),
    svc: CashService = Depends(_cash),
):
    return await svc.get_sessions(branch_id, limit=limit)


@router.post("/sessions/open", status_code=status.HTTP_201_CREATED)
async def open_session(
    payload: OpenSessionRequest,
    current_user: User = Depends(require_cashier),
    svc: CashService = Depends(_cash),
):
    return await svc.open_session(payload.branch_id, current_user.id, payload.opening_float)


@router.post("/sessions/{session_id}/close")
async def close_session(
    session_id: int,
    payload: CloseSessionRequest,
    _: User = Depends(require_cashier),
    svc: CashService = Depends(_cash),
):
    return await svc.close_session(session_id, payload.closing_float, payload.closure_notes)


@router.post("/sessions/{session_id}/transactions", status_code=status.HTTP_201_CREATED)
async def record_cash_transaction(
    session_id: int,
    payload: CashTransactionRequest,
    current_user: User = Depends(require_cashier),
    svc: CashService = Depends(_cash),
):
    return await svc.record_transaction(
        session_id,
        payload.transaction_type,
        payload.amount,
        payload.reason,
        authorized_by_id=current_user.id,
    )


@router.get("/sessions/{session_id}/transactions")
async def get_session_transactions(
    session_id: int,
    _: User = Depends(require_cashier),
    svc: CashService = Depends(_cash),
):
    return await svc.get_session_transactions(session_id)