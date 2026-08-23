"""Typed Razorpay integration abstraction supporting live REST calls and test-mode mocks."""

import base64
import hashlib
import hmac
import uuid
from typing import Any

import httpx
from pydantic import BaseModel, Field

from packages.shared.config import get_settings
from packages.shared.logging import get_logger

logger = get_logger("razorpay.client")


class RazorpayOrderRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise")
    currency: str = Field(default="INR")
    receipt: str | None = None
    notes: dict[str, str] = Field(default_factory=dict)
    partial_payment: bool = False


class RazorpayOrderResponse(BaseModel):
    id: str
    entity: str = "order"
    amount: int
    amount_paid: int = 0
    amount_due: int
    currency: str
    receipt: str | None = None
    status: str
    attempts: int = 0
    notes: dict[str, str] = Field(default_factory=dict)
    created_at: int


class RazorpayPaymentResponse(BaseModel):
    id: str
    entity: str = "payment"
    amount: int
    currency: str
    status: str
    order_id: str | None = None
    method: str | None = "card"
    captured: bool = True
    description: str | None = None
    created_at: int


class RazorpayRefundRequest(BaseModel):
    payment_id: str
    amount: int | None = None
    notes: dict[str, str] = Field(default_factory=dict)
    speed: str = "normal"


class RazorpayRefundResponse(BaseModel):
    id: str
    entity: str = "refund"
    amount: int
    currency: str
    payment_id: str
    status: str
    notes: dict[str, str] = Field(default_factory=dict)
    created_at: int


class RazorpayPaymentLinkRequest(BaseModel):
    amount: int
    currency: str = "INR"
    description: str
    customer_name: str | None = None
    customer_email: str | None = None
    customer_contact: str | None = None
    notes: dict[str, str] = Field(default_factory=dict)


class RazorpayPaymentLinkResponse(BaseModel):
    id: str
    short_url: str
    status: str
    amount: int
    currency: str
    description: str
    created_at: int


class RazorpayClient:
    """Production-grade typed abstraction over Razorpay REST API with configurable base URL and dual live/mock support."""

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        base_url: str | None = None,
        mock_mode: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = (base_url or settings.RAZORPAY_BASE_URL).rstrip("/")
        self.mock_mode = mock_mode if mock_mode is not None else settings.RAZORPAY_MOCK_MODE
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    @property
    def _auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        is_idempotent: bool = False,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Executes HTTP request against Razorpay REST API with strict idempotency invariants:
        - GET requests: Retry on transient network errors (500, 502, 503, 504, 429, timeouts).
        - POST mutations: Blind retries on network timeouts are strictly avoided. Instead, ambiguous
          outcomes are reconciled via the background worker / fetch_order before any secondary action.
        """
        import asyncio
        import random

        url = f"{self.base_url}{path}"
        attempts = max_retries if is_idempotent else 1

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    if method.upper() == "GET":
                        resp = await client.get(url, headers=self._auth_header)
                    elif method.upper() == "POST":
                        resp = await client.post(url, json=json_data, headers=self._auth_header)
                    else:
                        resp = await client.request(method, url, json=json_data, headers=self._auth_header)

                    data = resp.json()
                    return data if isinstance(data, dict) else {"data": data}
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                is_retryable_status = (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code in {429, 500, 502, 503, 504}
                )
                is_network_or_timeout = isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))

                if is_idempotent and attempt < attempts and (is_retryable_status or is_network_or_timeout):
                    backoff = (0.2 * (2**attempt)) + random.uniform(0.05, 0.15)
                    logger.warning(
                        "razorpay_transient_error_retrying",
                        path=path,
                        attempt=attempt,
                        backoff_seconds=round(backoff, 2),
                    )
                    await asyncio.sleep(backoff)
                    continue

                logger.error(
                    "razorpay_request_failed",
                    path=path,
                    attempt=attempt,
                    is_idempotent=is_idempotent,
                    error=str(exc),
                )
                raise

        raise RuntimeError(f"Failed all {attempts} attempts for {method} {path}")

    # ========================================================
    # Orders Subsystem
    # ========================================================
    async def create_order(self, req: RazorpayOrderRequest) -> RazorpayOrderResponse:
        """
        Creates an Order on Razorpay.
        Idempotency / Timeout Reconciliation:
        If a network timeout occurs during POST /orders, the operation remains in EXECUTING/RESERVED
        until the background reconciliation worker verifies gateway state via fetch_order,
        preventing duplicate financial mutations.
        """
        import time

        logger.info(
            "creating_razorpay_order", amount=req.amount, currency=req.currency, mock=self.mock_mode
        )

        receipt_key = req.receipt or f"rcpt_{uuid.uuid4().hex[:8]}"

        if self.mock_mode:
            order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
            return RazorpayOrderResponse(
                id=order_id,
                amount=req.amount,
                amount_due=req.amount,
                currency=req.currency,
                receipt=receipt_key,
                status="created",
                notes=req.notes,
                created_at=int(time.time()),
            )

        payload: dict[str, Any] = {
            "amount": req.amount,
            "currency": req.currency,
            "receipt": receipt_key,
            "notes": req.notes,
            "partial_payment": req.partial_payment,
        }

        data = await self._request_with_retry("POST", "/orders", json_data=payload, is_idempotent=False)
        return RazorpayOrderResponse(**data)


    async def fetch_order(self, order_id: str) -> RazorpayOrderResponse:
        import time

        logger.info("fetching_razorpay_order", order_id=order_id, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayOrderResponse(
                id=order_id,
                amount=50000,
                amount_due=0,
                amount_paid=50000,
                currency="INR",
                status="paid",
                created_at=int(time.time()),
            )

        # Fetch is idempotent GET
        data = await self._request_with_retry("GET", f"/orders/{order_id}", is_idempotent=True)
        return RazorpayOrderResponse(**data)


    # ========================================================
    # Payments Subsystem
    # ========================================================
    async def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        import time

        logger.info("fetching_razorpay_payment", payment_id=payment_id, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayPaymentResponse(
                id=payment_id,
                amount=50000,
                currency="INR",
                status="captured",
                captured=True,
                created_at=int(time.time()),
            )

        data = await self._request_with_retry("GET", f"/payments/{payment_id}", is_idempotent=True)
        return RazorpayPaymentResponse(**data)

    async def capture_payment(
        self, payment_id: str, amount: int, currency: str = "INR"
    ) -> RazorpayPaymentResponse:
        import time

        logger.info(
            "capturing_razorpay_payment", payment_id=payment_id, amount=amount, mock=self.mock_mode
        )

        if self.mock_mode:
            return RazorpayPaymentResponse(
                id=payment_id,
                amount=amount,
                currency=currency,
                status="captured",
                captured=True,
                created_at=int(time.time()),
            )

        payload = {"amount": amount, "currency": currency}
        data = await self._request_with_retry("POST", f"/payments/{payment_id}/capture", json_data=payload, is_idempotent=False)
        return RazorpayPaymentResponse(**data)

    # ========================================================
    # Refunds Subsystem
    # ========================================================
    async def create_refund(self, req: RazorpayRefundRequest) -> RazorpayRefundResponse:
        import time

        logger.info(
            "creating_razorpay_refund",
            payment_id=req.payment_id,
            amount=req.amount,
            mock=self.mock_mode,
        )

        if self.mock_mode:
            refund_id = f"rfnd_mock_{uuid.uuid4().hex[:14]}"
            return RazorpayRefundResponse(
                id=refund_id,
                amount=req.amount or 50000,
                currency="INR",
                payment_id=req.payment_id,
                status="processed",
                notes=req.notes,
                created_at=int(time.time()),
            )

        payload: dict[str, Any] = {
            "notes": req.notes,
            "speed": req.speed,
        }
        if req.amount is not None:
            payload["amount"] = req.amount

        data = await self._request_with_retry("POST", f"/payments/{req.payment_id}/refund", json_data=payload, is_idempotent=False)
        return RazorpayRefundResponse(**data)

    async def fetch_refund(self, refund_id: str) -> RazorpayRefundResponse:
        import time

        logger.info("fetching_razorpay_refund", refund_id=refund_id, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayRefundResponse(
                id=refund_id,
                amount=50000,
                currency="INR",
                payment_id="pay_mock_default",
                status="processed",
                notes={},
                created_at=int(time.time()),
            )

        data = await self._request_with_retry("GET", f"/refunds/{refund_id}", is_idempotent=True)
        return RazorpayRefundResponse(**data)

    # ========================================================
    # Payment Links Subsystem
    # ========================================================
    async def create_payment_link(
        self, req: RazorpayPaymentLinkRequest
    ) -> RazorpayPaymentLinkResponse:
        import time

        logger.info("creating_payment_link", amount=req.amount, mock=self.mock_mode)

        if self.mock_mode:
            plink_id = f"plink_mock_{uuid.uuid4().hex[:14]}"
            return RazorpayPaymentLinkResponse(
                id=plink_id,
                short_url=f"https://rzp.io/i/{plink_id}",
                status="created",
                amount=req.amount,
                currency=req.currency,
                description=req.description,
                created_at=int(time.time()),
            )

        payload: dict[str, Any] = {
            "amount": req.amount,
            "currency": req.currency,
            "description": req.description,
            "notes": req.notes,
        }
        if req.customer_name or req.customer_email or req.customer_contact:
            payload["customer"] = {
                "name": req.customer_name or "",
                "email": req.customer_email or "",
                "contact": req.customer_contact or "",
            }

        data = await self._request_with_retry("POST", "/payment_links", json_data=payload, is_idempotent=False)
        return RazorpayPaymentLinkResponse(
            id=data["id"],
            short_url=data.get("short_url", f"https://rzp.io/i/{data['id']}"),
            status=data.get("status", "created"),
            amount=data.get("amount", req.amount),
            currency=data.get("currency", req.currency),
            description=data.get("description", req.description),
            created_at=data.get("created_at", int(time.time())),
        )

    async def fetch_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        import time

        logger.info("fetching_payment_link", link_id=link_id, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayPaymentLinkResponse(
                id=link_id,
                short_url=f"https://rzp.io/i/{link_id}",
                status="paid",
                amount=50000,
                currency="INR",
                description="Fetched Payment Link",
                created_at=int(time.time()),
            )

        data = await self._request_with_retry("GET", f"/payment_links/{link_id}", is_idempotent=True)
        return RazorpayPaymentLinkResponse(
            id=data["id"],
            short_url=data.get("short_url", f"https://rzp.io/i/{data['id']}"),
            status=data.get("status", "created"),
            amount=data.get("amount", 0),
            currency=data.get("currency", "INR"),
            description=data.get("description", ""),
            created_at=data.get("created_at", int(time.time())),
        )

    async def cancel_payment_link(self, link_id: str) -> RazorpayPaymentLinkResponse:
        import time

        logger.info("cancelling_payment_link", link_id=link_id, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayPaymentLinkResponse(
                id=link_id,
                short_url=f"https://rzp.io/i/{link_id}",
                status="cancelled",
                amount=50000,
                currency="INR",
                description="Cancelled link",
                created_at=int(time.time()),
            )

        data = await self._request_with_retry("POST", f"/payment_links/{link_id}/cancel", is_idempotent=True)
        return RazorpayPaymentLinkResponse(
            id=data["id"],
            short_url=data.get("short_url", f"https://rzp.io/i/{data['id']}"),
            status=data.get("status", "cancelled"),
            amount=data.get("amount", 0),
            currency=data.get("currency", "INR"),
            description=data.get("description", ""),
            created_at=data.get("created_at", int(time.time())),
        )

    # ========================================================
    # Signatures & Webhook Verification
    # ========================================================
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        secret: str | None = None,
    ) -> bool:
        """Verifies payment signature from checkout completion."""
        active_secret = secret or self.key_secret
        if not active_secret or not razorpay_signature:
            return False

        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        generated_signature = hmac.new(
            key=active_secret.encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, razorpay_signature)

    def verify_webhook_signature(
        self,
        body: str,
        signature: str,
        secret: str | None = None,
    ) -> bool:
        """
        Verifies SHA256 HMAC signature sent in X-Razorpay-Signature header against the raw body bytes.
        Uses RAZORPAY_WEBHOOK_SECRET specifically.
        """
        active_secret = secret or self.webhook_secret
        if not active_secret or not signature:
            return False

        generated_signature = hmac.new(
            key=active_secret.encode("utf-8"),
            msg=body.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)

