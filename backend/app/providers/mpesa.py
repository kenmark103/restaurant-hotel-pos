"""
providers/mpesa.py — Safaricom M-Pesa Daraja API (STK Push / C2B)
─────────────────────────────────────────────────────────────────────────────
Implements the Lipa Na M-Pesa Online (STK Push) flow:
  1. initiate()  → POST /mpesa/stkpush/v1/processrequest
                   → Returns AWAITING_CONFIRMATION, merchant request ID stored
  2. callback    → handle_webhook()  — Daraja calls our /payments/webhooks/mpesa
                   → Extract ResultCode, MpesaReceiptNumber
  3. (optional)  → verify()  → POST /mpesa/stkpushquery/v1/query for polling

Requires env vars (set in .env):
  MPESA_CONSUMER_KEY
  MPESA_CONSUMER_SECRET
  MPESA_SHORTCODE         (BusinessShortCode / till number)
  MPESA_PASSKEY           (Lipa Na Mpesa passkey)
  MPESA_CALLBACK_URL      (publicly accessible URL, e.g. https://api.yourpos.com/payments/webhooks/mpesa)
  MPESA_ENVIRONMENT       (sandbox | production)

Reference: https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate
"""

import base64
import logging
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.providers.base import (
    BasePaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
_PROD_BASE = "https://api.safaricom.co.ke"


def _mpesa_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def _stk_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


class MpesaProvider(BasePaymentProvider):
    """
    M-Pesa STK Push provider.

    Inject in PaymentService via DI or by calling PaymentService.use_provider("mpesa").
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        shortcode: str,
        passkey: str,
        callback_url: str,
        environment: str = "sandbox",
    ) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._shortcode = shortcode
        self._passkey = passkey
        self._callback_url = callback_url
        self._base_url = _PROD_BASE if environment == "production" else _SANDBOX_BASE
        self._token_cache: str | None = None
        self._token_expires: datetime | None = None

    @property
    def name(self) -> str:
        return "mpesa"

    @property
    def supports_async_confirmation(self) -> bool:
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # OAuth token (cached for its lifetime minus a 30s buffer)
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        now = datetime.now(UTC)
        if self._token_cache and self._token_expires and now < self._token_expires:
            return self._token_cache

        credentials = base64.b64encode(
            f"{self._consumer_key}:{self._consumer_secret}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {credentials}"},
            )
            resp.raise_for_status()
            data = resp.json()

        self._token_cache = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        from datetime import timedelta
        self._token_expires = now + timedelta(seconds=expires_in - 30)
        return self._token_cache

    # ─────────────────────────────────────────────────────────────────────────
    # STK Push initiation
    # ─────────────────────────────────────────────────────────────────────────

    async def initiate(self, request: PaymentRequest) -> PaymentResult:
        """
        Send an STK Push prompt to the customer's phone.
        Returns AWAITING_CONFIRMATION with instructions.
        """
        if not request.customer_phone:
            return PaymentResult(
                status=ProviderStatus.FAILED,
                error_message="Customer phone number is required for M-Pesa payment.",
            )

        phone = self._normalise_phone(request.customer_phone)
        timestamp = _mpesa_timestamp()
        password = _stk_password(self._shortcode, self._passkey, timestamp)

        payload = {
            "BusinessShortCode": self._shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(request.amount),   # M-Pesa requires integer KES
            "PartyA": phone,
            "PartyB": self._shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self._callback_url,
            "AccountReference": request.reference,
            "TransactionDesc": request.description[:13],  # max 13 chars
        }

        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base_url}/mpesa/stkpush/v1/processrequest",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
        except Exception as exc:
            logger.error("M-Pesa STK initiation failed: %s", exc)
            return PaymentResult(
                status=ProviderStatus.FAILED,
                error_message=str(exc),
            )

        response_code = data.get("ResponseCode", "")
        if response_code != "0":
            return PaymentResult(
                status=ProviderStatus.FAILED,
                error_message=data.get("errorMessage") or data.get("ResponseDescription"),
                raw_response=data,
            )

        return PaymentResult(
            status=ProviderStatus.AWAITING_CONFIRMATION,
            provider_reference=data.get("CheckoutRequestID"),
            instructions=f"Check your phone ({request.customer_phone}) for the M-Pesa prompt.",
            raw_response=data,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STK Push query (polling alternative to waiting for callback)
    # ─────────────────────────────────────────────────────────────────────────

    async def verify(self, provider_reference: str) -> PaymentResult:
        timestamp = _mpesa_timestamp()
        password = _stk_password(self._shortcode, self._passkey, timestamp)
        payload = {
            "BusinessShortCode": self._shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": provider_reference,
        }
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base_url}/mpesa/stkpushquery/v1/query",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                data = resp.json()
        except Exception as exc:
            return PaymentResult(status=ProviderStatus.FAILED, error_message=str(exc))

        result_code = str(data.get("ResultCode", ""))
        if result_code == "0":
            return PaymentResult(
                status=ProviderStatus.SUCCESS,
                provider_reference=provider_reference,
                raw_response=data,
            )
        return PaymentResult(
            status=ProviderStatus.FAILED,
            error_message=data.get("ResultDesc"),
            raw_response=data,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Webhook / callback handler
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_webhook(self, payload: dict) -> PaymentResult:
        """
        Parse a Daraja STK Push callback body.
        Expected shape:
          {"Body": {"stkCallback": {"ResultCode": 0, "CallbackMetadata": {...}}}}
        """
        try:
            callback = payload["Body"]["stkCallback"]
            result_code = int(callback["ResultCode"])
            checkout_id = callback.get("CheckoutRequestID")

            if result_code != 0:
                return PaymentResult(
                    status=ProviderStatus.FAILED,
                    provider_reference=checkout_id,
                    error_message=callback.get("ResultDesc"),
                    raw_response=payload,
                )

            metadata_items = callback.get("CallbackMetadata", {}).get("Item", [])
            meta = {item["Name"]: item.get("Value") for item in metadata_items}
            receipt_number = str(meta.get("MpesaReceiptNumber", ""))

            return PaymentResult(
                status=ProviderStatus.SUCCESS,
                provider_reference=receipt_number or checkout_id,
                provider_status="paid",
                raw_response=payload,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("M-Pesa webhook parse error: %s — payload: %s", exc, payload)
            return PaymentResult(
                status=ProviderStatus.FAILED,
                error_message=f"Webhook parse error: {exc}",
                raw_response=payload,
            )

    @staticmethod
    def _normalise_phone(phone: str) -> str:
        """Convert +254XXXXXXXXX or 07XXXXXXXX → 2547XXXXXXXX."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("+"):
            phone = phone[1:]
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        return phone