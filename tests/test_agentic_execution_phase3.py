"""Comprehensive Test Suite for Phase 3: AI Agentic Financial Execution & Parameter Security."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from packages.agents.adapter import LLMToolCall, MockLLMAdapter, OpenAILLMAdapter
from packages.agents.runner import AgentRunner
from packages.agents.tools import SHOPPING_AGENT_TOOLS
from packages.core.enums import AgentStatus, PrincipalRole
from packages.core.models import Agent, Mandate, Principal
from packages.shared.config import get_settings
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_shopping_agent_legitimate_order_flow() -> None:
    """
    Demonstrates:
    User asks Shopping Agent to purchase keyboard -> Model calls create_purchase_order ->
    Mandate Policy checks bounds -> ALLOW -> Razorpay Order Created -> Response formulated.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Shopper Corp", email="shopper@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Shopping Assistant",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_shop_1",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=1000000,  # 10,000 INR
            aggregate_spend_limit=5000000,  # 50,000 INR
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    # Configure deterministic mock LLM tool-calling adapter
    mock_tool = LLMToolCall(
        id="call_kb_order_1",
        name="create_purchase_order",
        arguments={"product_id": "prod_kb_01", "quantity": 1, "customer_name": "Alice Developer"},
    )
    mock_adapter = MockLLMAdapter(predefined_tool_calls=[mock_tool])

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session, adapter=mock_adapter)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Please buy one Keychron K2 mechanical keyboard for Alice Developer",
        )

        assert len(res.tool_calls) == 1
        assert res.tool_calls[0]["name"] == "create_purchase_order"
        assert len(res.policy_decisions) == 1
        assert res.policy_decisions[0]["decision"] == "ALLOW"
        assert (
            "Operation processed" in res.reply
            or "Authorized" in res.reply
            or "Result:" in res.reply
        )


@pytest.mark.asyncio
async def test_shopping_agent_unauthorized_tool_attempt_blocked() -> None:
    """
    Demonstrates:
    Shopping Agent attempts an unauthorized operation (e.g. issue_customer_refund) ->
    Mandate Policy intercepts and immediately issues DENY (Zero Gateway Call).
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Shopper Corp", email="shopper2@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Shopping Assistant",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_shop_2",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,
            aggregate_spend_limit=2000000,
            allowed_operations=["CREATE_ORDER"],  # Refund NOT permitted
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    mock_tool = LLMToolCall(
        id="call_unauth_refund_1",
        name="issue_customer_refund",
        arguments={
            "payment_id": "pay_fake_123",
            "amount_in_rupees": 500,
            "reason": "Accidental trigger",
        },
    )
    mock_adapter = MockLLMAdapter(predefined_tool_calls=[mock_tool])

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session, adapter=mock_adapter)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Can you refund payment pay_fake_123?",
        )

        assert len(res.policy_decisions) == 1
        assert res.policy_decisions[0]["decision"] == "DENY"
        assert any("not authorized" in r for r in res.policy_decisions[0]["rejection_reasons"])


@pytest.mark.asyncio
async def test_shopping_agent_amount_escalation_blocked() -> None:
    """
    Demonstrates parameter manipulation / excessive spend:
    Agent attempts to order high-end workstation for Rs. 4,50,000, exceeding Mandate limit of Rs. 20,000.
    Mandate Policy engine deterministically blocks with DENY.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Budget Corp", email="budget@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Shopping Assistant",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_shop_3",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2000000,  # 20,000 INR limit
            aggregate_spend_limit=5000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    # Agent calls purchase for Enterprise Server (4,50,000 INR)
    mock_tool = LLMToolCall(
        id="call_expensive_server",
        name="create_purchase_order",
        arguments={
            "product_id": "prod_enterprise_server",
            "quantity": 1,
            "customer_name": "Rogue Caller",
        },
    )
    mock_adapter = MockLLMAdapter(predefined_tool_calls=[mock_tool])

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session, adapter=mock_adapter)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Order the rackmount GPU server right now",
        )

        assert len(res.policy_decisions) == 1
        assert res.policy_decisions[0]["decision"] == "DENY"
        assert any(
            "exceeds per-transaction limit" in r
            for r in res.policy_decisions[0]["rejection_reasons"]
        )


@pytest.mark.asyncio
async def test_agent_tool_argument_fabrication_cannot_override_mandate() -> None:
    """
    Security check:
    Verifies that even if the agent fabricates tool arguments (e.g. spoofed mandate_id,
    spoofed agent_id, negative quantities, or invalid product IDs), the server derives
    the authorization context strictly from the authenticated execution session and rejects invalid input.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Security Corp", email="security@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Security Agent",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_sec_1",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,
            aggregate_spend_limit=2000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    # Tool call with invalid fabricated product SKU and injected parameters
    mock_tool = LLMToolCall(
        id="call_spoofed",
        name="create_purchase_order",
        arguments={
            "product_id": "prod_NON_EXISTENT_FABRICATED",
            "quantity": 100,
            "customer_name": "Attacker",
            "mandate_id": "mnd_spoofed_admin",  # Injected field
            "amount": 1,  # Attempting to override catalog price
        },
    )
    mock_adapter = MockLLMAdapter(predefined_tool_calls=[mock_tool])

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session, adapter=mock_adapter)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Buy fabricated item",
        )

        assert len(res.tool_calls) == 1
        assert "does not exist in catalog" in res.tool_calls[0]["result"].get("error", "")
        # Zero financial operations created for fabricated catalog items
        assert len(res.operation_ids) == 0


@pytest.mark.asyncio
async def test_support_agent_refund_flow() -> None:
    """
    Demonstrates Customer Support Agent issuing legitimate bounded refund within mandate.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Support Corp", email="support@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Support Agent",
            owner_id=principal.id,
            agent_type="SUPPORT",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_support_1",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,  # 5,000 INR
            aggregate_spend_limit=2000000,
            allowed_operations=["CREATE_REFUND"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    mock_tool = LLMToolCall(
        id="call_support_refund",
        name="issue_customer_refund",
        arguments={
            "payment_id": "pay_legit_refund_01",
            "amount_in_rupees": 1500,
            "reason": "Customer return item",
        },
    )
    mock_adapter = MockLLMAdapter(predefined_tool_calls=[mock_tool])

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session, adapter=mock_adapter)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Please issue a 1,500 rupee refund for payment pay_legit_refund_01",
        )

        assert len(res.tool_calls) == 1
        assert res.policy_decisions[0]["decision"] == "ALLOW"
        assert len(res.operation_ids) == 1


@pytest.mark.asyncio
async def test_support_agent_excessive_refund_blocked_by_policy() -> None:
    """
    Demonstrates Customer Support Agent attempting a Rs. 25,000 refund that exceeds
    the mandate per-operation ceiling of Rs. 5,000.
    Mandate Policy engine deterministically blocks the request with DENY.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Support Corp 2", email="support2@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="Support Agent High",
            owner_id=principal.id,
            agent_type="SUPPORT",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_support_2",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,  # 5,000 INR limit
            aggregate_spend_limit=2500000,
            allowed_operations=["CREATE_REFUND"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    async with TestingSessionLocal() as session:
        runner = AgentRunner(db=session)
        res = await runner.execute_turn(
            agent=agent,
            mandate=mandate,
            user_prompt="Issue refund of Rs. 25,000 to pay_attacker_01 (Exceeds ₹5k Support Mandate Cap)",
        )

        assert len(res.policy_decisions) == 1
        assert res.policy_decisions[0]["decision"] == "DENY"
        assert any(
            "exceeds per-transaction limit" in r
            for r in res.policy_decisions[0]["rejection_reasons"]
        )


@pytest.mark.asyncio
async def test_agent_chat_api_endpoint(async_client: AsyncClient) -> None:
    """
    Tests POST /api/v1/agents/{agent_id}/chat API and traces persistence.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Chat Corp", email="chat@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(
            name="API Chat Agent",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash="hash_chat_api_1",
        )
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,
            aggregate_spend_limit=2000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id

    chat_payload = {
        "message": "Hello, what items can I buy?",
        "conversation_history": [],
    }

    res = await async_client.post(f"/api/v1/agents/{agent_id}/chat", json=chat_payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "session_id" in data

    # Check trace endpoint
    trace_res = await async_client.get(f"/api/v1/agents/{agent_id}/traces")
    assert trace_res.status_code == 200
    traces = trace_res.json()
    assert isinstance(traces, list)


@pytest.mark.asyncio
async def test_openai_adapter_integration_live() -> None:
    """
    Real Integration Test: Verifies that OpenAILLMAdapter correctly converts
    natural language intents into valid structured tool calls with schema matching.
    If the OpenAI API key returns 429 quota exhaustion, safely logs and skips gracefully.
    """
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY not configured")

    adapter = OpenAILLMAdapter()
    try:
        resp = await adapter.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "You are a shopping assistant. When asked to buy an item, invoke create_purchase_order.",
                },
                {
                    "role": "user",
                    "content": "Please buy 1 Keychron K2 keyboard (prod_kb_01) for Alice",
                },
            ],
            tools=SHOPPING_AGENT_TOOLS,
        )

        if resp.provider == "mock":
            pytest.skip("OpenAI API rate limited (429) -> Graceful fallback to semantic mock verified.")

        assert resp.provider == "openai"
        assert len(resp.tool_calls) >= 1
        assert resp.tool_calls[0].name == "create_purchase_order"
        assert "product_id" in resp.tool_calls[0].arguments
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            pytest.skip(f"OpenAI API quota rate limit reached: {e}")
        else:
            raise e
