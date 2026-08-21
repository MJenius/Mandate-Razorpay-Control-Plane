"""End-to-End Integration Flow Tests: Mandate -> Razorpay -> Webhook -> Settlement."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from packages.core.enums import MandateStatus, OperationStatus, PrincipalRole
from packages.core.models import Agent, FinancialOperation, Mandate, Principal
from packages.shared.config import get_settings


@pytest.mark.asyncio
async def test_full_order_payment_webhook_flow(async_client: AsyncClient) -> None:
    """
    Demonstrates:
    1. Create Principal & Agent
    2. Issue Bounded Mandate (Max Rs 500, Aggregate Rs 2,000)
    3. Agent Requests CREATE_ORDER through Mandate
    4. Razorpay Order is created in Test/Mock mode
    5. Signature Verification simulates user payment
    6. Razorpay Webhook is ingested (HMAC validated)
    7. State is settled and Audit Trail is persisted.
    """
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        principal = Principal(name="Alpha Corp", email="alpha@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="Autonomous Purchaser", owner_id=principal.id, api_key_hash="dummy_hash_123")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            status=MandateStatus.ACTIVE,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=200000,
            current_aggregate_spend=0,
            allowed_operations=["CREATE_ORDER", "CREATE_REFUND"],
            policy_config={},
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id
        mandate_id = mandate.id

    # 2. Agent Requests Financial Operation (CREATE_ORDER)
    idempotency_key = f"idemp_{uuid.uuid4().hex}"
    op_payload = {
        "idempotency_key": idempotency_key,
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 25000,
        "currency": "INR",
        "payload": {"receipt": "rcpt_001"},
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    op_data = res.json()
    assert op_data["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]
    assert op_data["amount"] == 25000
    op_id = op_data["operation_id"]

    # 3. Test Idempotency (Submitting the same idempotency_key returns cached operation)
    res_duplicate = await async_client.post("/api/v1/operations", json=op_payload)
    assert res_duplicate.status_code == 201
    assert res_duplicate.json()["operation_id"] == op_id

    # 4. Verify Payment Checkout Signature
    mock_order_id = "order_mock_test_123"
    mock_payment_id = "pay_mock_test_123"
    secret = get_settings().RAZORPAY_KEY_SECRET

    msg = f"{mock_order_id}|{mock_payment_id}".encode()
    valid_sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

    verify_res = await async_client.post(
        f"/api/v1/operations/{op_id}/verify-payment",
        json={
            "razorpay_order_id": mock_order_id,
            "razorpay_payment_id": mock_payment_id,
            "razorpay_signature": valid_sig,
        },
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["verified"] is True
    assert verify_res.json()["status"] == "SUCCEEDED"

    # 5. Ingest Razorpay Webhook (payment.captured)
    webhook_secret = get_settings().RAZORPAY_WEBHOOK_SECRET
    wh_event_id = f"wh_evt_{uuid.uuid4().hex[:12]}"
    wh_payload = {
        "entity": "event",
        "account_id": "acc_mock_1",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": mock_payment_id,
                    "order_id": mock_order_id,
                    "amount": 25000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    wh_body = json.dumps(wh_payload)
    wh_sig = hmac.new(webhook_secret.encode(), wh_body.encode(), hashlib.sha256).hexdigest()

    wh_res = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=wh_body,
        headers={
            "X-Razorpay-Signature": wh_sig,
            "X-Razorpay-Event-Id": wh_event_id,
            "Content-Type": "application/json",
        },
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] in ["PROCESSED", "processed"]

    # 6. Audit & History Inspection
    audit_res = await async_client.get(f"/api/v1/audit/resources/FINANCIAL_OPERATION/{op_id}")
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_full_refund_flow(async_client: AsyncClient) -> None:
    """
    Demonstrates:
    Mandate Issue -> Agent Requests Refund -> Policy Checked -> Razorpay Refund Executed ->
    Razorpay Webhook (refund.processed) -> Spend Credited Back -> Audit Trail Recorded.
    """
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as session:
        principal = Principal(name="Beta Corp", email="beta@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="Support Refund Agent", owner_id=principal.id, api_key_hash="dummy_refund_hash")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=10000,
            aggregate_spend_limit=50000,
            current_aggregate_spend=15000,
            allowed_operations=["CREATE_REFUND"],
            policy_config={},
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id
        mandate_id = mandate.id

    refund_op_payload = {
        "idempotency_key": f"idemp_rfnd_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_REFUND",
        "amount": 5000,
        "currency": "INR",
        "payload": {"payment_id": "pay_mock_to_refund"},
    }

    res = await async_client.post("/api/v1/operations", json=refund_op_payload)
    assert res.status_code == 201
    assert res.json()["status"] == "SUCCEEDED"

    # Webhook for refund processed
    webhook_secret = get_settings().RAZORPAY_WEBHOOK_SECRET
    wh_event_id = f"wh_rfnd_{uuid.uuid4().hex[:12]}"
    wh_payload = {
        "entity": "event",
        "event": "refund.processed",
        "payload": {
            "refund": {
                "entity": {
                    "id": "rfnd_mock_processed_99",
                    "payment_id": "pay_mock_to_refund",
                    "amount": 5000,
                    "currency": "INR",
                    "status": "processed",
                }
            }
        },
    }
    wh_body = json.dumps(wh_payload)
    wh_sig = hmac.new(webhook_secret.encode(), wh_body.encode(), hashlib.sha256).hexdigest()

    wh_res = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=wh_body,
        headers={
            "X-Razorpay-Signature": wh_sig,
            "X-Razorpay-Event-Id": wh_event_id,
            "Content-Type": "application/json",
        },
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] in ["PROCESSED", "processed"]
