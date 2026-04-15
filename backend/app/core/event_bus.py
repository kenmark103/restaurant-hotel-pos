"""
event_bus.py — Lightweight in-process domain event bus
─────────────────────────────────────────────────────────────────────────────
Decouples service domains without requiring an external message broker.
Events are dispatched synchronously within the same request context; later
they can be swapped for Celery/SQS tasks by changing the EventBus internals
without touching callers.

Domain event contracts (blueprint §3.2):
  • OrderSentToStations
  • OrderItemVoided
  • OrderClosed
  • PaymentRecorded
  • PrintRequested
  + extras for PIN/staff lifecycle

Usage:
    from app.core.event_bus import bus, OrderClosed

    # In POSService.close_order:
    await bus.publish(OrderClosed(order_id=order.id, payments=payment_data))

    # Elsewhere (e.g. a listener registered at startup):
    @bus.on(OrderClosed)
    async def handle_order_closed(event: OrderClosed) -> None:
        await print_service.generate_receipt(event.order_id)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine, Type, TypeVar

logger = logging.getLogger(__name__)

E = TypeVar("E", bound="DomainEvent")
Handler = Callable[[Any], Coroutine[Any, Any, None]]


# ─────────────────────────────────────────────────────────────────────────────
# Base event
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DomainEvent:
    """All domain events inherit from this.  timestamp is set automatically."""

    timestamp: datetime = field(default_factory=datetime.utcnow, init=False)


# ─────────────────────────────────────────────────────────────────────────────
# POS domain events
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderSentToStations(DomainEvent):
    """Fired after send_to_kitchen() creates KDS tickets."""

    order_id: int
    branch_id: int
    station_ids: list[str]      # all stations notified
    item_ids: list[int]         # order_item IDs that were sent


@dataclass
class OrderItemVoided(DomainEvent):
    order_id: int
    order_item_id: int
    menu_item_name: str
    quantity: int
    reason: str
    voided_by_id: int
    branch_id: int


@dataclass
class OrderClosed(DomainEvent):
    order_id: int
    branch_id: int
    total_amount: Decimal
    payments: list[dict]        # [{method, amount, reference}, ...]
    staff_user_id: int


@dataclass
class PaymentRecorded(DomainEvent):
    order_id: int
    branch_id: int
    method: str
    amount: Decimal
    reference: str | None


@dataclass
class PrintRequested(DomainEvent):
    job_type: str               # receipt | station_ticket | z_report | reprint
    order_id: int | None
    branch_id: int
    requested_by_id: int
    payload_snapshot: dict      # data needed to render the print job


# ─────────────────────────────────────────────────────────────────────────────
# Identity / staff events
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StaffPinSet(DomainEvent):
    staff_user_id: int
    branch_id: int
    set_by_id: int


@dataclass
class StaffPinLocked(DomainEvent):
    staff_user_id: int
    branch_id: int
    locked_until: datetime


@dataclass
class StaffActivated(DomainEvent):
    staff_user_id: int
    branch_id: int | None


# ─────────────────────────────────────────────────────────────────────────────
# Inventory events
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LowStockAlert(DomainEvent):
    branch_id: int
    menu_item_id: int
    menu_item_name: str
    current_stock: Decimal
    threshold: int


# ─────────────────────────────────────────────────────────────────────────────
# Event bus
# ─────────────────────────────────────────────────────────────────────────────

class EventBus:
    """
    Simple, in-process pub/sub bus.

    - Handlers are registered once at application startup.
    - publish() is async — handlers are awaited sequentially (safe for DB ops).
    - Handler exceptions are caught and logged; they never abort the caller.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = {}

    def on(self, event_type: type[E]) -> Callable[[Handler], Handler]:
        """Decorator to register an async handler for *event_type*."""

        def decorator(fn: Handler) -> Handler:
            self._handlers.setdefault(event_type, []).append(fn)
            return fn

        return decorator

    def register(self, event_type: type[E], handler: Handler) -> None:
        """Programmatic alternative to the @bus.on decorator."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """
        Dispatch *event* to all registered handlers.

        Errors in individual handlers are caught + logged so a failing
        side-effect never rolls back the primary transaction.
        """
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s",
                    handler.__qualname__,
                    type(event).__name__,
                )

bus = EventBus()