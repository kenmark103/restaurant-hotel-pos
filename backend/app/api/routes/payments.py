"""
routes/payments.py
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_cashier
from app.core.event_bus import bus
from app.db.models import PaymentMethod, User
from app.db.session import get_db
from app.schemas.payments import InitiatePaymentRequest, PaymentResultResponse, VerifyPaymentRequest
from app.services.payment_service import PaymentService

router = APIRouter()


def _pay(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> PaymentService:
    return PaymentService(db, user, event_bus=bus)


@router.post("/initiate", response_model=PaymentResultResponse)
async def initiate_payment(
    payload: InitiatePaymentRequest,
    _: User = Depends(require_cashier),
    svc: PaymentService = Depends(_pay),
):
    result = await svc.initiate_payment(
        order_id=payload.order_id,
        method=payload.method,
        amount=payload.amount,
        customer_phone=payload.customer_phone,
        customer_email=payload.customer_email,
        reference=payload.reference,
        record_only=payload.record_only,
    )
    return PaymentResultResponse(
        status=result.status,
        provider_reference=result.provider_reference,
        checkout_url=result.checkout_url,
        instructions=result.instructions,
        error_message=result.error_message,
    )


@router.post("/verify", response_model=PaymentResultResponse)
async def verify_payment(
    payload: VerifyPaymentRequest,
    _: User = Depends(require_cashier),
    svc: PaymentService = Depends(_pay),
):
    result = await svc.verify_payment(payload.method, payload.provider_reference)
    return PaymentResultResponse(status=result.status, provider_reference=result.provider_reference)


# ── Webhook handlers (no auth — validated by provider signature) ──────────────

@router.post("/webhooks/mpesa", status_code=status.HTTP_200_OK)
async def mpesa_webhook(
    request: Request,
    order_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.json()
    svc = PaymentService(db, current_user=None, event_bus=bus)
    await svc.handle_webhook(PaymentMethod.MOBILE_MONEY, payload, order_id=order_id)
    # M-Pesa expects {"ResultCode": 0, "ResultDesc": "Accepted"}
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/webhooks/pesapal", status_code=status.HTTP_200_OK)
async def pesapal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.json()
    svc = PaymentService(db, current_user=None, event_bus=bus)
    order_id = payload.get("OrderMerchantReference")
    await svc.handle_webhook(PaymentMethod.CARD, payload, order_id=int(order_id) if order_id else None)
    return {"status": "received"}