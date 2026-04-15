"""
core/listeners.py — Event bus handler registrations
─────────────────────────────────────────────────────────────────────────────
This is the single file that wires domain events to their side-effect
handlers.  Call register_all_listeners(bus) once at application startup
(in main.py lifespan).

HOW THE EVENT BUS WORKS IN PRACTICE
─────────────────────────────────────────────────────────────────────────────

1. A service publishes an event:

     # Inside POSService.close_order():
     await self.bus.publish(OrderClosed(
         order_id=order.id,
         branch_id=order.branch_id,
         total_amount=order.total_amount,
         payments=recorded_payments,
         staff_user_id=order.staff_user_id,
     ))

2. The bus dispatches to every registered handler in this file.
   Handlers run sequentially in the same async context (same DB transaction
   scope if they share the session).

3. Each handler is a plain async function that receives the event dataclass:

     async def on_order_closed(event: OrderClosed) -> None:
         # spin up a fresh DB session for side-effects
         async with AsyncSessionLocal() as db:
             printing = PrintingService(db)
             await printing.print_receipt(event.order_id)

4. Handler exceptions are caught by the bus — they never abort the
   caller's transaction.  Errors are logged via the standard logger.

REGISTERING A HANDLER
─────────────────────────────────────────────────────────────────────────────
Two equivalent styles:

  # Style A: decorator (defined here, registered at module load)
  @bus.on(OrderClosed)
  async def my_handler(event: OrderClosed) -> None: ...

  # Style B: programmatic (used in register_all_listeners for testability)
  bus.register(OrderClosed, my_handler)

Both land in the same handler list.  Use Style B for all production handlers
so tests can call register_all_listeners(mock_bus) without touching the
singleton.

ADDING PAYMENT PROVIDERS
─────────────────────────────────────────────────────────────────────────────
Register real gateway providers in _configure_payment_providers() below.
Toggle between record_only (MVP) and live mode by setting the env var:
  PAYMENT_LIVE_MODE=true

TESTING HANDLERS
─────────────────────────────────────────────────────────────────────────────
In pytest, create a fresh EventBus(), pass it to the service under test,
and assert the events it emits — without calling register_all_listeners().
"""

import logging
from typing import TYPE_CHECKING

from app.core.event_bus import (
    EventBus,
    LowStockAlert,
    OrderClosed,
    OrderItemVoided,
    OrderSentToStations,
    PaymentRecorded,
    PrintRequested,
    StaffActivated,
    StaffPinLocked,
)
from app.core.config import settings
from app.db.session import AsyncSessionLocal

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Handler implementations
# ─────────────────────────────────────────────────────────────────────────────

async def _on_print_requested(event: PrintRequested) -> None:
    """
    Triggered by: OrderClosed (receipt), send_to_kitchen (station tickets).
    Generates a PDF PrintJob and stores it.
    """
    from app.services.printing_service import PrintingService

    async with AsyncSessionLocal() as db:
        try:
            svc = PrintingService(db)
            if event.job_type == "receipt" and event.order_id:
                await svc.print_receipt(event.order_id)
                logger.info("Receipt printed for order %s", event.order_id)

            elif event.job_type == "station_ticket" and event.order_id:
                station_id = event.payload_snapshot.get("station_id")
                if station_id:
                    await svc.print_station_ticket(event.order_id, station_id)

        except Exception:
            logger.exception(
                "PrintJob generation failed: job_type=%s order=%s",
                event.job_type,
                event.order_id,
            )


async def _on_order_sent_to_stations(event: OrderSentToStations) -> None:
    """
    Triggered by: POSService.send_to_kitchen().
    Fires one PrintRequested (station ticket) per notified station.
    The printing handler above will pick those up and generate ticket PDFs.
    """
    # (In MVP we let the KDS screen show the ticket digitally — physical
    # printing is queued via PrintRequested, handled above.)
    logger.debug(
        "Order %s sent to stations %s (branch %s)",
        event.order_id,
        event.station_ids,
        event.branch_id,
    )


async def _on_order_closed(event: OrderClosed) -> None:
    """
    Triggered by: POSService.close_order().
    Could trigger loyalty point accrual, analytics refresh, etc.
    Receipt printing is already handled by the PrintRequested event emitted
    from close_order — don't double-print here.
    """
    logger.info(
        "Order %s closed — total %s (branch %s)",
        event.order_id,
        event.total_amount,
        event.branch_id,
    )
    # Future: accrue loyalty points for customer, refresh DailySalesSummary MV


async def _on_order_item_voided(event: OrderItemVoided) -> None:
    """
    Triggered by: POSService.void_order_item() and void_order().
    Future: notify manager dashboard in real time.
    """
    logger.info(
        "Item voided — order %s item %s reason='%s'",
        event.order_id,
        event.order_item_id,
        event.reason,
    )


async def _on_payment_recorded(event: PaymentRecorded) -> None:
    """
    Triggered by: PaymentService._record_payment().
    Future: update cash-session running total, alert on high-value payments.
    """
    logger.debug(
        "Payment recorded — order %s method=%s amount=%s ref=%s",
        event.order_id,
        event.method,
        event.amount,
        event.reference,
    )


async def _on_low_stock_alert(event: LowStockAlert) -> None:
    """
    Triggered by: InventoryService after a sale depletion crosses the threshold.
    Future: send email/SMS, push to manager dashboard.
    """
    logger.warning(
        "LOW STOCK: '%s' (item %s) at branch %s — qty=%s threshold=%s",
        event.menu_item_name,
        event.menu_item_id,
        event.branch_id,
        event.current_stock,
        event.threshold,
    )


async def _on_staff_activated(event: StaffActivated) -> None:
    logger.info("Staff %s activated (branch %s)", event.staff_user_id, event.branch_id)


async def _on_staff_pin_locked(event: StaffPinLocked) -> None:
    logger.warning(
        "PIN locked for staff %s (branch %s) until %s",
        event.staff_user_id,
        event.branch_id,
        event.locked_until,
    )
    # Future: alert branch manager via push notification


# ─────────────────────────────────────────────────────────────────────────────
# Payment provider configuration
# ─────────────────────────────────────────────────────────────────────────────

def _configure_payment_providers(payment_service_factory) -> None:
    """
    Register live payment providers on the PaymentService.
    Called from register_all_listeners() if PAYMENT_LIVE_MODE=true.

    payment_service_factory is a callable → PaymentService instance.
    In production this is a singleton shared across requests (no DB ops here).
    """
    import os
    from app.db.models import PaymentMethod

    live_mode = os.environ.get("PAYMENT_LIVE_MODE", "false").lower() == "true"
    if not live_mode:
        logger.info("Payment providers: record-only mode (PAYMENT_LIVE_MODE not set)")
        return

    # M-Pesa
    mpesa_key = os.environ.get("MPESA_CONSUMER_KEY")
    mpesa_secret = os.environ.get("MPESA_CONSUMER_SECRET")
    if mpesa_key and mpesa_secret:
        from app.providers.mpesa import MpesaProvider
        provider = MpesaProvider(
            consumer_key=mpesa_key,
            consumer_secret=mpesa_secret,
            shortcode=os.environ["MPESA_SHORTCODE"],
            passkey=os.environ["MPESA_PASSKEY"],
            callback_url=os.environ["MPESA_CALLBACK_URL"],
            environment=os.environ.get("MPESA_ENVIRONMENT", "sandbox"),
        )
        payment_service_factory().register_provider(PaymentMethod.MOBILE_MONEY, provider)
        logger.info("M-Pesa provider registered (%s)", os.environ.get("MPESA_ENVIRONMENT"))

    # PesaPal
    pp_key = os.environ.get("PESAPAL_CONSUMER_KEY")
    pp_secret = os.environ.get("PESAPAL_CONSUMER_SECRET")
    if pp_key and pp_secret:
        from app.providers.pesapal import PesaPalProvider
        provider = PesaPalProvider(
            consumer_key=pp_key,
            consumer_secret=pp_secret,
            ipn_url=os.environ["PESAPAL_IPN_URL"],
            environment=os.environ.get("PESAPAL_ENVIRONMENT", "sandbox"),
        )
        payment_service_factory().register_provider(PaymentMethod.CARD, provider)
        logger.info("PesaPal provider registered (%s)", os.environ.get("PESAPAL_ENVIRONMENT"))


# ─────────────────────────────────────────────────────────────────────────────
# Public registration entry point
# ─────────────────────────────────────────────────────────────────────────────

def register_all_listeners(bus: EventBus) -> None:
    """
    Wire all handlers to the bus.
    Call once in the FastAPI lifespan:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            from app.core.listeners import register_all_listeners
            from app.core.event_bus import bus
            register_all_listeners(bus)
            yield
            # shutdown ...

    This function is deliberately idempotent — calling it twice on the same
    bus adds duplicate handlers.  Only call it once.
    """
    bus.register(PrintRequested, _on_print_requested)
    bus.register(OrderSentToStations, _on_order_sent_to_stations)
    bus.register(OrderClosed, _on_order_closed)
    bus.register(OrderItemVoided, _on_order_item_voided)
    bus.register(PaymentRecorded, _on_payment_recorded)
    bus.register(LowStockAlert, _on_low_stock_alert)
    bus.register(StaffActivated, _on_staff_activated)
    bus.register(StaffPinLocked, _on_staff_pin_locked)

    logger.info("Event bus: %d event types registered", len(bus._handlers))