"""Tests for Hierarchical Delegation Edge Cases: Upward Spend Propagation, In-Flight Revocation Settlement, and Risk Agent Scoring."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from packages.agents.delegation import CollaborativeCommerceCoordinator
from packages.core.enums import (
    PrincipalRole,
)
from packages.core.models import Agent, Mandate, Principal
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_hierarchical_budget_spend_propagation_upward(async_client: AsyncClient) -> None:
    """
    Edge Case 1: Hierarchical Spend Accounting
    When a child mandate commits spend upon successful payment, the spend accounting
    must correctly commit at the child level AND reduce the unallocated pool at the parent level.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Hierarchical Spend Corp", email="spend@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        parent_agent = Agent(
            name="Parent Shopping Agent",
            owner_id=principal.id,
            agent_type="SHOPPING",
            api_key_hash="hash_h_p",
        )
        child_agent = Agent(
            name="Child Procurement Agent",
            owner_id=principal.id,
            agent_type="PROCUREMENT",
            api_key_hash="hash_h_c",
        )
        session.add_all([parent_agent, child_agent])
        await session.flush()

        # Root parent mandate: ₹1,00,000 limit
        root_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000,
            aggregate_spend_limit=10000000,  # ₹1,00,000
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(root_mandate)
        await session.commit()
        parent_id = root_mandate.id
        child_agent_id = child_agent.id

    # 1. Delegate ₹20,000 to child
    del_res = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "max_amount_per_op": 1000000,
            "aggregate_spend_limit": 2000000,  # ₹20,000
            "allowed_operations": ["CREATE_ORDER"],
            "valid_until": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        },
    )
    assert del_res.status_code == 201
    child_id = del_res.json()["id"]

    # 2. Child executes ₹6,500 order
    op_res = await async_client.post(
        "/api/v1/operations",
        json={
            "idempotency_key": f"idemp_child_spend_{uuid.uuid4().hex}",
            "agent_id": child_agent_id,
            "mandate_id": child_id,
            "operation_type": "CREATE_ORDER",
            "amount": 650000,
            "currency": "INR",
            "payload": {},
        },
    )
    assert op_res.status_code == 201
    op_id = op_res.json()["operation_id"]

    # 3. Simulate payment verification
    import hashlib
    import hmac

    from packages.shared.config import get_settings

    secret = get_settings().RAZORPAY_KEY_SECRET
    msg = f"order_mock_{op_id[:8]}|pay_mock_{op_id[:8]}".encode()
    valid_sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

    v_res = await async_client.post(
        f"/api/v1/operations/{op_id}/verify-payment",
        json={
            "razorpay_order_id": f"order_mock_{op_id[:8]}",
            "razorpay_payment_id": f"pay_mock_{op_id[:8]}",
            "razorpay_signature": valid_sig,
        },
    )
    assert v_res.status_code == 200

    # 4. Verify Accounting: Child has ₹6,500 committed spend; Parent tracked child allocated pool
    async with TestingSessionLocal() as session:
        ref_child = await session.get(Mandate, child_id)
        assert ref_child.current_aggregate_spend == 650000
        assert ref_child.reserved_spend == 0

        ref_parent = await session.get(Mandate, parent_id)
        assert ref_parent.delegated_child_budget_allocated == 2000000


@pytest.mark.asyncio
async def test_in_flight_operation_settlement_after_parent_revocation(
    async_client: AsyncClient,
) -> None:
    """
    Edge Case 2: In-Flight Operation Settlement Post-Revocation
    Deterministic Rule:
    If a child operation was already POLICY_APPROVED & RESERVED before parent revocation,
    when Razorpay captures payment, the webhook settles the already-reserved funds cleanly
    (avoiding budget drift/leakage), while any new child requests are strictly blocked.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="InFlight Corp", email="inflight@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        parent_agent = Agent(
            name="InFlight Parent", owner_id=principal.id, api_key_hash="hash_if_p"
        )
        child_agent = Agent(name="InFlight Child", owner_id=principal.id, api_key_hash="hash_if_c")
        session.add_all([parent_agent, child_agent])
        await session.flush()

        parent_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=3000000,
            aggregate_spend_limit=10000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(parent_mandate)
        await session.commit()
        parent_id = parent_mandate.id
        child_agent_id = child_agent.id

    # 1. Delegate child mandate
    del_res = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "max_amount_per_op": 1000000,
            "aggregate_spend_limit": 2000000,
            "allowed_operations": ["CREATE_ORDER"],
            "valid_until": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        },
    )
    assert del_res.status_code == 201
    child_id = del_res.json()["id"]

    # 2. Child dispatches order -> RESERVED & EXECUTING
    op_res = await async_client.post(
        "/api/v1/operations",
        json={
            "idempotency_key": f"idemp_inflight_{uuid.uuid4().hex}",
            "agent_id": child_agent_id,
            "mandate_id": child_id,
            "operation_type": "CREATE_ORDER",
            "amount": 500000,  # ₹5,000
            "currency": "INR",
            "payload": {},
        },
    )
    assert op_res.status_code == 201
    op_id = op_res.json()["operation_id"]

    # 3. Parent is suddenly REVOKED
    rev_res = await async_client.post(
        f"/api/v1/mandates/{parent_id}/revoke", json={"reason": "Compromised admin key"}
    )
    assert rev_res.status_code == 200

    # 4. In-flight webhook arrives from Razorpay for the pre-authorized order
    import hashlib
    import hmac
    import json

    from packages.shared.config import get_settings

    webhook_secret = get_settings().RAZORPAY_WEBHOOK_SECRET
    wh_payload = {
        "event_id": f"evt_inflight_{uuid.uuid4().hex[:8]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_inflight_01",
                    "order_id": f"order_mock_{op_id[:8]}",
                    "amount": 500000,
                    "status": "captured",
                }
            },
        },
    }
    raw_bytes = json.dumps(wh_payload).encode("utf-8")
    sig = hmac.new(webhook_secret.encode(), raw_bytes, hashlib.sha256).hexdigest()

    wh_res = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "PROCESSED"

    # 5. Verify new child operations are blocked
    new_op_res = await async_client.post(
        "/api/v1/operations",
        json={
            "idempotency_key": f"idemp_post_rev_{uuid.uuid4().hex}",
            "agent_id": child_agent_id,
            "mandate_id": child_id,
            "operation_type": "CREATE_ORDER",
            "amount": 100000,
            "currency": "INR",
            "payload": {},
        },
    )
    assert new_op_res.json()["status"] == "POLICY_REJECTED"


@pytest.mark.asyncio
async def test_risk_evaluation_agent_structured_signal_flow() -> None:
    """
    Edge Case 3: Risk Evaluation Agent Functional Influence
    Verifies that CollaborativeCommerceCoordinator evaluates structured Risk Agent scores
    and successfully routes through Mandate without letting the risk agent self-authorize.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Risk Commerce Corp", email="risk@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        parent_agent = Agent(
            name="Master Shopping Bot",
            owner_id=principal.id,
            agent_type="SHOPPING",
            api_key_hash="hash_rc_p",
        )
        child_agent = Agent(
            name="Procurement Sub Bot",
            owner_id=principal.id,
            agent_type="PROCUREMENT",
            api_key_hash="hash_rc_c",
        )
        session.add_all([parent_agent, child_agent])
        await session.flush()

        root_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000,
            aggregate_spend_limit=10000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(root_mandate)
        await session.flush()

        child_mandate = Mandate(
            agent_id=child_agent.id,
            granted_by_id=principal.id,
            parent_mandate_id=root_mandate.id,
            currency="INR",
            max_amount_per_op=1000000,  # ₹10,000
            aggregate_spend_limit=2000000,  # ₹20,000
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=15),
        )
        session.add(child_mandate)
        await session.commit()

        coordinator = CollaborativeCommerceCoordinator(db=session)
        collab_result = await coordinator.execute_procurement_flow(
            shopping_agent=parent_agent,
            procurement_agent=child_agent,
            child_mandate=child_mandate,
            product_id="prod_kb_01",
            quantity=1,
            customer_name="Alice Verified",
        )

        assert collab_result.policy_decision == "ALLOW"
        assert collab_result.risk_score < 0.50
        assert collab_result.total_amount_paise == 650000
        assert collab_result.operation_id is not None
