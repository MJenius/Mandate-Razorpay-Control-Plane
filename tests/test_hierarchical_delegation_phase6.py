"""Comprehensive Test Suite for Phase 6: Multi-Agent Delegation & Hierarchical Financial Authority."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from packages.core.enums import AgentStatus, MandateStatus, PrincipalRole
from packages.core.models import Agent, Mandate, Principal
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_hierarchical_mandate_delegation_flow(async_client: AsyncClient) -> None:
    """
    Demonstrates Legitimate Delegation:
    Principal -> Grants Root Mandate (₹1,00,000) to Primary Shopping Agent ->
    Shopping Agent delegates ₹15,000 child mandate to Procurement Sub-Agent ->
    Procurement Agent executes valid ₹6,500 purchase order through Mandate -> ALLOW.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Commerce Enterprise", email="commerce@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        parent_agent = Agent(name="Primary Shopping Agent", owner_id=principal.id, agent_type="SHOPPING", api_key_hash="hash_p6_parent")
        child_agent = Agent(name="Procurement Sub-Agent", owner_id=principal.id, agent_type="PROCUREMENT", api_key_hash="hash_p6_child")
        session.add_all([parent_agent, child_agent])
        await session.flush()

        # Root parent mandate: ₹1,00,000 limit, ₹25,000 per-op limit
        root_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000, # ₹25,000
            aggregate_spend_limit=10000000, # ₹1,00,000
            allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(root_mandate)
        await session.commit()
        parent_id = root_mandate.id
        child_agent_id = child_agent.id

    # 1. Delegate Sub-Mandate (₹15,000 limit, ₹10,000 per-op)
    delegate_payload = {
        "target_agent_id": child_agent_id,
        "max_amount_per_op": 1000000, # ₹10,000 (<= ₹25,000)
        "aggregate_spend_limit": 1500000, # ₹15,000 (<= ₹1,00,000)
        "allowed_operations": ["CREATE_ORDER"],
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
    }

    del_res = await async_client.post(f"/api/v1/mandates/{parent_id}/delegate", json=delegate_payload)
    assert del_res.status_code == 201
    child_mandate_data = del_res.json()
    assert child_mandate_data["parent_mandate_id"] == parent_id
    assert child_mandate_data["delegation_depth"] == 1
    child_mandate_id = child_mandate_data["id"]

    # 2. Child Agent executes compliant purchase order under delegated sub-mandate
    op_payload = {
        "idempotency_key": f"idemp_child_op_{uuid.uuid4().hex}",
        "agent_id": child_agent_id,
        "mandate_id": child_mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 650000, # ₹6,500 Keychron Keyboard
        "currency": "INR",
        "payload": {"product_id": "prod_kb_01", "quantity": 1},
    }

    op_res = await async_client.post("/api/v1/operations", json=op_payload)
    assert op_res.status_code == 201
    op_data = op_res.json()
    assert op_data["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]
    assert op_data["policy_evaluation_details"]["decision"] == "ALLOW"


@pytest.mark.asyncio
async def test_child_delegation_privilege_escalation_blocked(async_client: AsyncClient) -> None:
    """
    Demonstrates Mathematical Non-Escalation Guarantees:
    Parent has ₹25,000 per-op limit and ['CREATE_ORDER'] permission.
    1. Child asks for ₹50,000 per-op limit -> BLOCKED.
    2. Child asks for unpermitted ['CREATE_REFUND'] -> BLOCKED.
    3. Child asks for USD currency -> BLOCKED.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Escalation Corp", email="esc@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        parent_agent = Agent(name="Parent Agent", owner_id=principal.id, api_key_hash="hash_esc_parent")
        child_agent = Agent(name="Rogue Child", owner_id=principal.id, api_key_hash="hash_esc_child")
        session.add_all([parent_agent, child_agent])
        await session.flush()

        parent_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000, # ₹25,000
            aggregate_spend_limit=5000000, # ₹50,000
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(parent_mandate)
        await session.commit()
        parent_id = parent_mandate.id
        child_agent_id = child_agent.id

    # Test 1: Amount Escalation (Child asks for ₹50,000 vs Parent ₹25,000)
    res1 = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "max_amount_per_op": 5000000, # ₹50,000
            "aggregate_spend_limit": 5000000,
            "allowed_operations": ["CREATE_ORDER"],
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
    )
    assert res1.status_code == 400
    assert "Privilege escalation: Requested max_amount_per_op" in res1.json()["detail"]

    # Test 2: Permission Escalation (Child asks for CREATE_REFUND not in parent whitelist)
    res2 = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "max_amount_per_op": 1000000,
            "aggregate_spend_limit": 2000000,
            "allowed_operations": ["CREATE_REFUND"], # Unpermitted in parent
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
    )
    assert res2.status_code == 400
    assert "not authorized in parent mandate whitelist" in res2.json()["detail"]

    # Test 3: Currency Spoofing (Child asks for USD vs Parent INR)
    res3 = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "currency": "USD",
            "max_amount_per_op": 100000,
            "aggregate_spend_limit": 100000,
            "allowed_operations": ["CREATE_ORDER"],
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
    )
    assert res3.status_code == 400
    assert "Child currency 'USD' does not match parent bound 'INR'" in res3.json()["detail"]


@pytest.mark.asyncio
async def test_cascading_parent_revocation_blocks_child_transactions(async_client: AsyncClient) -> None:
    """
    Demonstrates Cascading Revocation Propagation:
    1. Parent grants child mandate.
    2. Revoking/suspending the parent mandate instantly propagates down the tree.
    3. Child transactions immediately evaluate to DENY with zero gateway side-effects.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Cascade Corp", email="cascade@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        parent_agent = Agent(name="Shopping Master", owner_id=principal.id, api_key_hash="hash_cas_p")
        child_agent = Agent(name="Procurement Sub", owner_id=principal.id, api_key_hash="hash_cas_c")
        session.add_all([parent_agent, child_agent])
        await session.flush()

        parent_mandate = Mandate(
            agent_id=parent_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=3000000,
            aggregate_spend_limit=10000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(parent_mandate)
        await session.commit()
        parent_id = parent_mandate.id
        child_agent_id = child_agent.id

    # 1. Delegate Sub-mandate
    del_res = await async_client.post(
        f"/api/v1/mandates/{parent_id}/delegate",
        json={
            "target_agent_id": child_agent_id,
            "max_amount_per_op": 1000000,
            "aggregate_spend_limit": 2000000,
            "allowed_operations": ["CREATE_ORDER"],
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        },
    )
    assert del_res.status_code == 201
    child_mandate_id = del_res.json()["id"]

    # 2. Revoke Parent Mandate
    rev_res = await async_client.post(f"/api/v1/mandates/{parent_id}/revoke", json={"reason": "Compromised credential"})
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "REVOKED"

    # Verify Child Mandate status was automatically cascaded to REVOKED
    child_status_res = await async_client.get(f"/api/v1/mandates/{child_mandate_id}")
    assert child_status_res.status_code == 200
    assert child_status_res.json()["status"] == "REVOKED"

    # 3. Attempt Child Transaction -> Deterministically DENIED
    op_res = await async_client.post(
        "/api/v1/operations",
        json={
            "idempotency_key": f"idemp_revoked_child_{uuid.uuid4().hex}",
            "agent_id": child_agent_id,
            "mandate_id": child_mandate_id,
            "operation_type": "CREATE_ORDER",
            "amount": 150000,
            "currency": "INR",
            "payload": {},
        },
    )
    assert op_res.status_code == 201
    data = op_res.json()
    assert data["status"] == "POLICY_REJECTED"
    assert "Mandate status is REVOKED" in data["error_message"]
