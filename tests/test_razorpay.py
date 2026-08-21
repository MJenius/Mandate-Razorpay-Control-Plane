"""Tests for Razorpay integration client abstraction."""

import pytest

from packages.razorpay.client import (
    RazorpayClient,
    RazorpayOrderRequest,
    RazorpayPaymentLinkRequest,
    RazorpayRefundRequest,
)


@pytest.mark.asyncio
async def test_razorpay_order_creation_mock() -> None:
    client = RazorpayClient(mock_mode=True)
    req = RazorpayOrderRequest(amount=100000, currency="INR", receipt="receipt_01")
    order = await client.create_order(req)
    assert order.id.startswith("order_mock_")
    assert order.amount == 100000
    assert order.status == "created"


@pytest.mark.asyncio
async def test_razorpay_refund_mock() -> None:
    client = RazorpayClient(mock_mode=True)
    req = RazorpayRefundRequest(payment_id="pay_12345", amount=5000)
    refund = await client.create_refund(req)
    assert refund.id.startswith("rfnd_mock_")
    assert refund.amount == 5000
    assert refund.status == "processed"


@pytest.mark.asyncio
async def test_razorpay_payment_link_mock() -> None:
    client = RazorpayClient(mock_mode=True)
    req = RazorpayPaymentLinkRequest(amount=25000, description="Test Payment Link")
    plink = await client.create_payment_link(req)
    assert plink.id.startswith("plink_mock_")
    assert plink.amount == 25000
    assert "rzp.io" in plink.short_url


def test_razorpay_webhook_signature_verification() -> None:
    import hashlib
    import hmac

    client = RazorpayClient(mock_mode=True)
    secret = "sample_webhook_secret_key"
    payload = '{"event":"payment.captured"}'

    # Valid signature
    expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    assert client.verify_webhook_signature(payload, expected_sig, secret=secret) is True

    # Invalid signature
    assert client.verify_webhook_signature(payload, "invalid_signature", secret=secret) is False
