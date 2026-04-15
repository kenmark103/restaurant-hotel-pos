"""
routes/kitchen.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_kitchen
from app.core.websocket_manager import websocket_manager
from app.db.models import KdsTicketStatus, User
from app.db.session import get_db
from app.services.kitchen_service import KitchenService

router = APIRouter()


def _kitchen(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> KitchenService:
    return KitchenService(db, user, websocket_manager=websocket_manager)


@router.get("/tickets")
async def list_tickets(
    branch_id: int,
    station_id: Optional[str] = None,
    ticket_status: Optional[KdsTicketStatus] = None,
    _: User = Depends(require_kitchen),
    svc: KitchenService = Depends(_kitchen),
):
    return await svc.get_station_tickets(station_id=station_id, branch_id=branch_id, status=ticket_status)


@router.patch("/tickets/{ticket_id}/status")
async def bump_ticket(
    ticket_id: int,
    new_status: KdsTicketStatus,
    current_user: User = Depends(require_kitchen),
    svc: KitchenService = Depends(_kitchen),
):
    return await svc.update_ticket_status(ticket_id, new_status)


@router.post("/tickets/{ticket_id}/rush")
async def escalate_ticket(
    ticket_id: int,
    _: User = Depends(require_kitchen),
    svc: KitchenService = Depends(_kitchen),
):
    return await svc.escalate_priority(ticket_id)


@router.get("/stations/{station_id}/metrics")
async def station_metrics(
    station_id: str,
    _: User = Depends(require_kitchen),
    svc: KitchenService = Depends(_kitchen),
):
    return await svc.get_station_metrics(station_id)


@router.websocket("/ws/{branch_id}/{station_id}")
async def kitchen_ws(
    websocket: WebSocket,
    branch_id: int,
    station_id: str,
    db: AsyncSession = Depends(get_db),
):
    room = f"branch_{branch_id}_kitchen_{station_id}"
    await websocket_manager.connect(websocket, room)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, room)