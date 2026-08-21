"""Typed Razorpay integration abstraction supporting live REST calls and test-mode mocks."""

import base64
import hashlib
import hmac
import uuid
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field
from packages.shared.config import get_settings
from packages.shared.logging import get_logger

logger = get_logger("razorpay.client")


class RazorpayOrderRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in paise")
    currency: str = Field(default="INR")
    receipt: Optional[str] = None
    notes: Dict[str, str] = Field(default_factory=dict)
    partial_payment: bool = False


class RazorpayOrderResponse(BaseModel):
    id: str
    entity: str = "order"
    amount: int
    amount_paid: int = 0
    amount_due: int
    currency: str
    receipt: Optional[str] = None
    status: str
    attempts: int = 0
    notes: Dict[str, str] = Field(default_factory=dict)
    created_at: int


class RazorpayPaymentResponse(BaseModel):
    id: str
    entity: str = "payment"
    amount: int
    currency: str
    status: str
    order_id: Optional[str] = None
    method: Optional[str] = "card"
    captured: bool = True
    description: Optional[str] = None
    created_at: int


class RazorpayRefundRequest(BaseModel):
    payment_id: str
    amount: Optional[int] = None
    notes: Dict[str, str] = Field(default_factory=dict)
    speed: str = "normal"


class RazorpayRefundResponse(BaseModel):
    id: str
    entity: str = "refund"
    amount: int
    currency: str
    payment_id: str
    status: str
    notes: Dict[str, str] = Field(default_factory=dict)
    created_at: int


class RazorpayPaymentLinkRequest(BaseModel):
    amount: int
    currency: str = "INR"
    description: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_contact: Optional[str] = None
    notes: Dict[str, str] = Field(default_factory=dict)


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
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        settings = get_settings()
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = (base_url or settings.RAZORPAY_BASE_URL).rstrip("/")
        self.mock_mode = mock_mode if mock_mode is not None else settings.RAZORPAY_MOCK_MODE
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    @property
    def _auth_header(self) -> Dict[str, str]:
        token = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    # ========================================================
    # Orders Subsystem
    # ========================================================
    async def create_order(self, req: RazorpayOrderRequest) -> RazorpayOrderResponse:
        import time
        logger.info("creating_razorpay_order", amount=req.amount, currency=req.currency, mock=self.mock_mode)

        if self.mock_mode:
            order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
            return RazorpayOrderResponse(
                id=order_id,
                amount=req.amount,
                amount_due=req.amount,
                currency=req.currency,
                receipt=req.receipt or f"rcpt_{uuid.uuid4().hex[:8]}",
                status="created",
                notes=req.notes,
                created_at=int(time.time()),
            )

        payload: Dict[str, Any] = {
            "amount": req.amount,
            "currency": req.currency,
            "receipt": req.receipt or f"rcpt_{uuid.uuid4().hex[:8]}",
            "notes": req.notes,
            "partial_payment": req.partial_payment,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/orders",
                json=payload,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            data = resp.json()
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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/orders/{order_id}",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return RazorpayOrderResponse(**resp.json())

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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return RazorpayPaymentResponse(**resp.json())

    async def capture_payment(self, payment_id: str, amount: int, currency: str = "INR") -> RazorpayPaymentResponse:
        import time
        logger.info("capturing_razorpay_payment", payment_id=payment_id, amount=amount, mock=self.mock_mode)

        if self.mock_mode:
            return RazorpayPaymentResponse(
                id=payment_id,
                amount=amount,
                currency=currency,
                status="captured",
                captured=True,
                created_at=int(time.time()),
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/payments/{payment_id}/capture",
                json={"amount": amount, "currency": currency},
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return RazorpayPaymentResponse(**resp.json())

    # ========================================================
    # Refunds Subsystem
    # ========================================================
    async def create_refund(self, req: RazorpayRefundRequest) -> RazorpayRefundResponse:
        import time
        logger.info("creating_razorpay_refund", payment_id=req.payment_id, amount=req.amount, mock=self.mock_mode)

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

        payload: Dict[str, Any] = {
            "notes": req.notes,
            "speed": req.speed,
        }
        if req.amount is not None:
            payload["amount"] = req.amount

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/payments/{req.payment_id}/refund",
                json=payload,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return RazorpayRefundResponse(**resp.json())

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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/refunds/{refund_id}",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            return RazorpayRefundResponse(**resp.json())

    # ========================================================
    # Payment Links Subsystem
    # ========================================================
    async def create_payment_link(self, req: RazorpayPaymentLinkRequest) -> RazorpayPaymentLinkResponse:
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

        payload: Dict[str, Any] = {
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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/payment_links",
                json=payload,
                headers=self._auth_header,
            )
            resp.raise_for_status()
            data = resp.json()
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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/payment_links/{link_id}",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            data = resp.json()
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

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/payment_links/{link_id}/cancel",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            data = resp.json()
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
        secret: Optional[str] = None,
    ) -> bool:
        """Verifies payment signature from checkout completion."""
        active_secret = secret or self.key_secret
        if not active_secret or not razorpay_signature:
            return False

        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
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
        secret: Optional[str] = None,
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
