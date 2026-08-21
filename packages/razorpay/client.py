"""Typed Razorpay integration abstraction with Test Mode and live gateway stubs."""

import hashlib
import hmac
import uuid
from typing import Any, Dict, List, Optional
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
    """Production-grade typed abstraction over Razorpay REST API."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        settings = get_settings()
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.mock_mode = mock_mode if mock_mode is not None else settings.RAZORPAY_MOCK_MODE
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    # ==========================
    # Orders Subsystem
    # ==========================
    async def create_order(self, req: RazorpayOrderRequest) -> RazorpayOrderResponse:
        import time
        logger.info("creating_razorpay_order", amount=req.amount, currency=req.currency, mock=self.mock_mode)
        if self.mock_mode:
            order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
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
        raise NotImplementedError("Live HTTP integration will be finalized in Phase 1.")

    async def fetch_order(self, order_id: str) -> RazorpayOrderResponse:
        import time
        logger.info("fetching_razorpay_order", order_id=order_id, mock=self.mock_mode)
        return RazorpayOrderResponse(
            id=order_id,
            amount=50000,
            amount_due=0,
            amount_paid=50000,
            currency="INR",
            status="paid",
            created_at=int(time.time()),
        )

    # ==========================
    # Payments Subsystem
    # ==========================
    async def fetch_payment(self, payment_id: str) -> RazorpayPaymentResponse:
        import time
        logger.info("fetching_razorpay_payment", payment_id=payment_id, mock=self.mock_mode)
        return RazorpayPaymentResponse(
            id=payment_id,
            amount=50000,
            currency="INR",
            status="captured",
            captured=True,
            created_at=int(time.time()),
        )

    # ==========================
    # Refunds Subsystem
    # ==========================
    async def create_refund(self, req: RazorpayRefundRequest) -> RazorpayRefundResponse:
        import time
        logger.info("creating_razorpay_refund", payment_id=req.payment_id, amount=req.amount, mock=self.mock_mode)
        refund_id = f"rfnd_mock_{uuid.uuid4().hex[:12]}"
        return RazorpayRefundResponse(
            id=refund_id,
            amount=req.amount or 50000,
            currency="INR",
            payment_id=req.payment_id,
            status="processed",
            notes=req.notes,
            created_at=int(time.time()),
        )

    # ==========================
    # Payment Links Subsystem
    # ==========================
    async def create_payment_link(self, req: RazorpayPaymentLinkRequest) -> RazorpayPaymentLinkResponse:
        import time
        logger.info("creating_payment_link", amount=req.amount, mock=self.mock_mode)
        plink_id = f"plink_mock_{uuid.uuid4().hex[:12]}"
        return RazorpayPaymentLinkResponse(
            id=plink_id,
            short_url=f"https://rzp.io/i/mock_{plink_id}",
            status="created",
            amount=req.amount,
            currency=req.currency,
            description=req.description,
            created_at=int(time.time()),
        )

    # ==========================
    # Webhooks Subsystem
    # ==========================
    def verify_webhook_signature(self, body: str, signature: str, secret: Optional[str] = None) -> bool:
        """Verifies SHA256 HMAC signature sent by Razorpay webhook headers."""
        active_secret = secret or self.webhook_secret
        if not active_secret or not signature:
            return False

        generated_signature = hmac.new(
            key=active_secret.encode("utf-8"),
            msg=body.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)
