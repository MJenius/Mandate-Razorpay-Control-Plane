"""Comprehensive Test Suite for Phase 7: Razorpay-Native Agentic Commerce & MCP Protocol Gateway."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from packages.core.enums import AgentStatus, MandateStatus, PrincipalRole
from packages.core.models import Agent, Mandate, Principal
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_mcp_gateway_initialize_and_tools_list(async_client: AsyncClient) -> None:
    """
    Tests standard MCP protocol initialize and dynamic tool filtering (tools/list):
    Shopping agent only receives permitted buyer tools, slashes 35+ tools down to 3.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="MCP Shopper Corp", email="mcpshop@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="MCP Shopping Bot", owner_id=principal.id, agent_type="SHOPPING", api_key_hash="hash_mcp_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000,
            aggregate_spend_limit=5000000,
            allowed_operations=["CREATE_ORDER"],  # Only orders permitted
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id

    # 1. MCP initialize call
    init_req = {"jsonrpc": "2.0", "id": "init_1", "method": "initialize", "params": {}}
    init_res = await async_client.post("/api/v1/mcp", json=init_req, headers={"X-Agent-Id": agent_id})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["result"]["protocolVersion"] == "2024-11-05"

    # 2. MCP tools/list call (Dynamic Filter check)
    tools_req = {"jsonrpc": "2.0", "id": "list_1", "method": "tools/list", "params": {}}
    tools_res = await async_client.post("/api/v1/mcp", json=tools_req, headers={"X-Agent-Id": agent_id})
    assert tools_res.status_code == 200
    tools_data = tools_res.json()
    exposed_tools = [t["name"] for t in tools_data["result"]["tools"]]

    # Invariant: payments_create_order is exposed; payouts_create & payments_create_refund are NOT exposed
    assert "payments_create_order" in exposed_tools
    assert "payouts_create" not in exposed_tools
    assert "payments_create_refund" not in exposed_tools


@pytest.mark.asyncio
async def test_mcp_gateway_tools_call_order_creation(async_client: AsyncClient) -> None:
    """
    Tests standard MCP tools/call dispatching payments_create_order through Mandate authorization.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="MCP Order Corp", email="mcporder@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="MCP Order Bot", owner_id=principal.id, agent_type="SHOPPING", api_key_hash="hash_mcp_2")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2000000, # ₹20,000
            aggregate_spend_limit=5000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id

    call_req = {
        "jsonrpc": "2.0",
        "id": "call_1",
        "method": "tools/call",
        "params": {
            "name": "payments_create_order",
            "arguments": {
                "amount": 650000, # ₹6,500
                "currency": "INR",
                "receipt": "rcpt_mcp_01",
            },
        },
    }

    call_res = await async_client.post("/api/v1/mcp", json=call_req, headers={"X-Agent-Id": agent_id})
    assert call_res.status_code == 200
    res_data = call_res.json()
    assert res_data["result"]["_mandate_meta"]["decision"] == "ALLOW"
    assert res_data["result"]["_mandate_meta"]["status"] in ["EXECUTING", "POLICY_APPROVED", "RESERVED"]


@pytest.mark.asyncio
async def test_mcp_gateway_rejects_unauthorized_unexpected_parameters(async_client: AsyncClient) -> None:
    """
    Strict Schema Validation Invariant:
    Injecting unauthorized parameters (e.g. 'mandate_override', 'bypass_token') must be strictly
    rejected with JSON-RPC error rather than silently stripped or mutated.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Strict Corp", email="strict@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="Strict Agent", owner_id=principal.id, api_key_hash="hash_mcp_3")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2000000,
            aggregate_spend_limit=5000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id = agent.id

    # Injected rogue parameter 'bypass_token'
    call_req = {
        "jsonrpc": "2.0",
        "id": "call_rogue_1",
        "method": "tools/call",
        "params": {
            "name": "payments_create_order",
            "arguments": {
                "amount": 100000,
                "currency": "INR",
                "bypass_token": "GRANT_ALL_ACCESS", # Unauthorized field
            },
        },
    }

    call_res = await async_client.post("/api/v1/mcp", json=call_req, headers={"X-Agent-Id": agent_id})
    assert call_res.status_code == 200
    res_data = call_res.json()
    assert "error" in res_data
    assert "Schema validation error" in res_data["error"]["message"]
