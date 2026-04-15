"""
providers/pesapal.py — PesaPal payment gateway
─────────────────────────────────────────────────────────────────────────────
PesaPal supports card, M-Pesa, Airtel Money, and bank transfer through a
single hosted checkout page (redirect flow + IPN callback).

Flow:
  1. initiate()     → POST /api/Transactions/SubmitOrderRequest
                       → Returns order_tracking_id + redirect_url
                       → Frontend opens redirect_url in a webview / new tab
  2. IPN callback   → handle_webhook()  — PesaPal calls our IPN URL
                       → Extract OrderNotificationType, MerchantReference
  3. verify()       → GET /api/Transactions/GetTransactionStatus?orderTrackingId=...
                       → Confirm payment_status_description == "Completed"

Requires env vars:
  PESAPAL_CONSUMER_KEY
  PESAPAL_CONSUMER_SECRET
  PESAPAL_IPN_URL             (e.g. https://api.yourpos.com/payments/webhooks/pesapal)
  PESAPAL_ENVIRONMENT         (sandbox | live)

Reference: https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/api-reference
"""

import logging
from decimal import Decimal

import httpx

from app.providers.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://cybqa.pesapal.com/pesapalv3"
_LIVE_BASE = "https://pay.pesapal.com/v3"


class PesaPalProvider(BasePaymentProvider):

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        ipn_url: str,
        environment: str = "sandbox",
    ) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._ipn_url = ipn_url
        self._base_url = _LIVE_BASE if environment == "live" else _SANDBOX_BASE
        self._token_cache: str | None = None
        self._ipn_id: str | None = None  # Registered IPN ID (one-time setup)

    @property
    def name(self) -> str:
        return "pesapal"

    @property
    def supports_async_confirmation(self) -> bool:
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        if self._token_cache:
            return self._token_cache
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/api/Auth/RequestToken",
                json={
                    "consumer_key": self._consumer_key,
                    "consumer_secret": self._consumer_secret,
                },
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        self._token_cache = data["token"]
        return self._token_cache

    # ─────────────────────────────────────────────────────────────────────────
    # IPN registration (call once at startup or on first payment)
    # ─────────────────────────────────────────────────────────────────────────

    async def _ensure_ipn_registered(self, token: str) -> str:
        if self._ipn_id:
            return self._ipn_id
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/api/URLSetup/RegisterIPN",
                json={"url": self._ipn_url, "ipn_notification_type": "POST"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        self._ipn_id = data["ipn_id"]
        return self._ipn_id

    # ─────────────────────────────────────────────────────────────────────────
    # Submit order (returns redirect URL)
    # ─────────────────────────────────────────────────────────────────────────

    async def initiate(self, request: PaymentRequest) -> PaymentResult:
        try:
            token = await self._get_token()
            ipn_id = await self._ensure_ipn_registered(token)

            order_payload = {
                "id": request.reference,
                "currency": request.currency,
                "amount": float(request.amount),
                "description": request.description,
                "callback_url": self._ipn_url,
                "notification_id": ipn_id,
                "billing_address": {
                    "email_address": request.customer_email or "",
                    "phone_number": request.customer_phone or "",
                },
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base_url}/api/Transactions/SubmitOrderRequest",
                    json=order_payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                data = resp.json()
        except Exception as exc:
            logger.error("PesaPal initiation failed: %s", exc)
            return PaymentResult(status=ProviderStatus.FAILED, error_message=str(exc))

        if data.get("status") == "200":
            return PaymentResult(
                status=ProviderStatus.AWAITING_CONFIRMATION,
                provider_reference=data.get("order_tracking_id"),
                checkout_url=data.get("redirect_url"),
                instructions="Complete payment on the PesaPal page.",
                raw_response=data,
            )

        return PaymentResult(
            status=ProviderStatus.FAILED,
            error_message=data.get("message") or "PesaPal order submission failed.",
            raw_response=data,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Transaction status query
    # ─────────────────────────────────────────────────────────────────────────

    async def verify(self, provider_reference: str) -> PaymentResult:
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self._base_url}/api/Transactions/GetTransactionStatus",
                    params={"orderTrackingId": provider_reference},
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
        except Exception as exc:
            return PaymentResult(status=ProviderStatus.FAILED, error_message=str(exc))

        status_desc = (data.get("payment_status_description") or "").lower()
        if status_desc == "completed":
            return PaymentResult(
                status=ProviderStatus.SUCCESS,
                provider_reference=data.get("confirmation_code") or provider_reference,
                provider_status=status_desc,
                raw_response=data,
            )
        if status_desc in ("invalid", "failed", "reversed"):
            return PaymentResult(
                status=ProviderStatus.FAILED,
                provider_status=status_desc,
                error_message=data.get("description"),
                raw_response=data,
            )
        return PaymentResult(
            status=ProviderStatus.PENDING,
            provider_reference=provider_reference,
            provider_status=status_desc,
            raw_response=data,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # IPN webhook handler
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_webhook(self, payload: dict) -> PaymentResult:
        """
        PesaPal IPN POST body:
          {"OrderNotificationType": "IPNCHANGE", "OrderTrackingId": "...",
           "OrderMerchantReference": "...", "OrderPaymentStatus": "Completed"}
        """
        try:
            tracking_id = payload.get("OrderTrackingId") or payload.get("orderTrackingId")
            status = (payload.get("OrderPaymentStatus") or "").lower()

            if status == "completed":
                return await self.verify(tracking_id)

            return PaymentResult(
                status=ProviderStatus.PENDING,
                provider_reference=tracking_id,
                provider_status=status,
                raw_response=payload,
            )
        except Exception as exc:
            logger.error("PesaPal webhook parse error: %s", exc)
            return PaymentResult(
                status=ProviderStatus.FAILED,
                error_message=str(exc),
                raw_response=payload,
            )