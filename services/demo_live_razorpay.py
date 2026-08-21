"""Live Razorpay Test Mode integration script."""

import asyncio
import os
import sys
from packages.razorpay.client import (
    RazorpayClient,
    RazorpayOrderRequest,
    RazorpayPaymentLinkRequest,
)
from packages.shared.config import get_settings
from packages.shared.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("demo.live_razorpay")


async def run_live_test() -> None:
    settings = get_settings()
    print("================================================================")
    print("   Mandate — Live Razorpay Test Mode Verification")
    print("================================================================")
    print(f"Key ID: {settings.RAZORPAY_KEY_ID[:8]}********")
    print(f"Mock Mode: {settings.RAZORPAY_MOCK_MODE}")
    print("----------------------------------------------------------------")

    client = RazorpayClient(mock_mode=False)

    try:
        # 1. Create Real Test Order
        print("\n1. Dispatching Real Razorpay Test Order...")
        order_req = RazorpayOrderRequest(
            amount=50000, # 500 INR
            currency="INR",
            receipt="rcpt_live_demo_01",
            notes={"purpose": "Mandate Phase 1 Live Verification"},
        )
        order = await client.create_order(order_req)
        print(f"   [SUCCESS] Order Created: {order.id}")
        print(f"   Amount: ₹{order.amount / 100:.2f} | Status: {order.status}")

        # 2. Create Real Test Payment Link
        print("\n2. Dispatching Real Razorpay Test Payment Link...")
        plink_req = RazorpayPaymentLinkRequest(
            amount=25000, # 250 INR
            currency="INR",
            description="Mandate Agent Authorized Spend",
            customer_name="Test AI User",
            customer_email="agent.test@mandate.dev",
        )
        plink = await client.create_payment_link(plink_req)
        print(f"   [SUCCESS] Payment Link Created: {plink.id}")
        print(f"   Hosted URL: {plink.short_url}")
        print(f"   Amount: ₹{plink.amount / 100:.2f} | Status: {plink.status}")

        print("\n================================================================")
        print("   Live Razorpay API Integration Verified Successfully!")
        print("================================================================\n")

    except Exception as e:
        print(f"\n[ERROR] Razorpay Live API Call Failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_live_test())
