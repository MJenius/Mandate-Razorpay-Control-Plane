"""Comprehensive test suite for Phase 2: Mandate Authorization & Deterministic Policy Engine."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from packages.core.enums import AgentStatus, MandateStatus, PrincipalRole
from packages.core.models import Agent, Mandate, Principal
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_policy_engine_allow_and_budget_reservation(async_client: AsyncClient) -> None:
    """Verifies that an eligible operation enters RESERVED state and dispatches order."""
    async with TestingSessionLocal() as session:
        principal = Principal(name="Acme Corp", email="acme@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="ProcureBot", owner_id=principal.id, api_key_hash="hash_p2_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            current_aggregate_spend=0,
            reserved_spend=0,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    op_payload = {
        "idempotency_key": f"idemp_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 40000,
        "currency": "INR",
        "payload": {},
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]
    assert data["policy_evaluation_details"]["decision"] == "ALLOW"

    # Verify budget reservation in mandate
    mandate_res = await async_client.get(f"/api/v1/mandates/{mandate_id}")
    assert mandate_res.status_code == 200
    mandate_data = mandate_res.json()
    assert mandate_data["reserved_spend"] == 40000
    assert mandate_data["current_aggregate_spend"] == 0


@pytest.mark.asyncio
async def test_policy_engine_rejection_suspended_agent(async_client: AsyncClient) -> None:
    """Verifies that operations from a SUSPENDED agent produce DENY with zero gateway call."""
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Suspended Corp", email="suspend@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="RogueBot",
            owner_id=principal.id,
            status=AgentStatus.SUSPENDED,
            api_key_hash="hash_p2_2",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    op_payload = {
        "idempotency_key": f"idemp_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 10000,
        "currency": "INR",
        "payload": {},
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "POLICY_REJECTED"
    assert data["policy_evaluation_details"]["decision"] == "DENY"
    assert any(
        "must be ACTIVE" in r for r in data["policy_evaluation_details"]["rejection_reasons"]
    )


@pytest.mark.asyncio
async def test_policy_engine_rejection_revoked_mandate(async_client: AsyncClient) -> None:
    """Verifies that revoked mandates immediately reject all operation intents."""
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Revoke Corp", email="revoke@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="ValidBot", owner_id=principal.id, api_key_hash="hash_p2_3")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            status=MandateStatus.REVOKED,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    op_payload = {
        "idempotency_key": f"idemp_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 10000,
        "currency": "INR",
        "payload": {},
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "POLICY_REJECTED"
    assert "REVOKED" in data["error_message"]


@pytest.mark.asyncio
async def test_policy_engine_human_review_threshold_flow(async_client: AsyncClient) -> None:
    """Verifies that amounts exceeding review threshold trigger REQUIRE_HUMAN_REVIEW until approved."""
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Review Corp", email="review@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="BigSpenderBot", owner_id=principal.id, api_key_hash="hash_p2_4")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=100000,
            aggregate_spend_limit=500000,
            review_threshold_amount=25000,  # Requires human review for >= 25k
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id, principal_id = agent.id, mandate.id, principal.id

    # 1. Request 30k (exceeds 25k review threshold)
    op_payload = {
        "idempotency_key": f"idemp_review_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 30000,
        "currency": "INR",
        "payload": {},
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "REQUIRES_APPROVAL"
    assert data["policy_evaluation_details"]["decision"] == "REQUIRE_HUMAN_REVIEW"
    op_id = data["operation_id"]

    # 2. Human Approves the Operation
    approve_res = await async_client.post(
        f"/api/v1/operations/{op_id}/approve",
        json={"approved_by_id": principal_id, "approved": True},
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]
    assert approved_data["approved_by_id"] == principal_id


@pytest.mark.asyncio
async def test_concurrent_spend_exhaustion_safety(async_client: AsyncClient) -> None:
    """
    Concurrency safety test:
    Total budget = 50,000. Each request = 25,000.
    Spawn 6 concurrent requests.
    Exactly 2 must be ALLOWED, and 4 must be DENIED (overspending strictly prevented).
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Parallel Corp", email="parallel@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="ConcurrentBot", owner_id=principal.id, api_key_hash="hash_p2_5")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=25000,
            aggregate_spend_limit=50000,  # Room for exactly 2 operations of 25,000
            current_aggregate_spend=0,
            reserved_spend=0,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    async def send_op(idx: int):
        payload = {
            "idempotency_key": f"idemp_concurrent_{idx}_{uuid.uuid4().hex}",
            "agent_id": agent_id,
            "mandate_id": mandate_id,
            "operation_type": "CREATE_ORDER",
            "amount": 25000,
            "currency": "INR",
            "payload": {},
        }
        return await async_client.post("/api/v1/operations", json=payload)

    # Dispatch 6 parallel requests
    tasks = [send_op(i) for i in range(6)]
    responses = await asyncio.gather(*tasks)

    allowed_count = 0
    denied_count = 0

    for r in responses:
        assert r.status_code == 201
        data = r.json()
        if data["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]:
            allowed_count += 1
        elif data["status"] == "POLICY_REJECTED":
            denied_count += 1

    assert allowed_count == 2
    assert denied_count == 4

    # Verify final mandate budget
    mandate_res = await async_client.get(f"/api/v1/mandates/{mandate_id}")
    m_data = mandate_res.json()
    assert m_data["reserved_spend"] + m_data["current_aggregate_spend"] == 50000
