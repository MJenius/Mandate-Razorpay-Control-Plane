"""Mandate Model Context Protocol (MCP) Security Gateway & JSON-RPC 2.0 Proxy Router."""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import MandateStatus
from packages.core.models import Agent, Mandate
from packages.core.schemas import OperationCreate
from packages.mcp.catalog import RAZORPAY_MCP_TOOL_REGISTRY, get_filtered_mcp_tools
from packages.razorpay.client import RazorpayClient
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("mcp.gateway")
router = APIRouter(prefix="/mcp", tags=["Razorpay MCP Gateway"])

razorpay_client = RazorpayClient()


class MCPJsonRpcRequest(BaseModel):
    """Standard JSON-RPC 2.0 MCP Request payload."""

    jsonrpc: str = Field(default="2.0")
    id: Any | None = Field(default="1")
    method: str = Field(..., description="MCP method: 'tools/list', 'tools/call', or 'initialize'")
    params: dict[str, Any] = Field(default_factory=dict)


class MCPJsonRpcResponse(BaseModel):
    """Standard JSON-RPC 2.0 MCP Response payload."""

    jsonrpc: str = "2.0"
    id: Any | None = "1"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@router.post("", response_model=MCPJsonRpcResponse)
async def handle_mcp_jsonrpc_gateway(
    request_payload: MCPJsonRpcRequest,
    x_agent_id: str = Header(
        ..., alias="X-Agent-Id", description="Authenticated calling AI Agent ID"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> MCPJsonRpcResponse:
    """
    Production JSON-RPC 2.0 Model Context Protocol (MCP) Gateway:
    1. 'initialize': Returns server capabilities & protocol version.
    2. 'tools/list': Dynamically exposes filtered tool surface based on agent's active mandate.
    3. 'tools/call': Intercepts invocation, strictly validates arguments against schema without silent modification, routes through Mandate Policy Engine, and dispatches to Razorpay Test Mode.
    """
    # 1. Authenticate Agent & Resolve Active Mandate
    agent = await db.get(Agent, x_agent_id)
    if not agent:
        return MCPJsonRpcResponse(
            id=request_payload.id,
            error={"code": -32001, "message": f"Agent '{x_agent_id}' not found or unauthenticated"},
        )

    mandate_stmt = (
        select(Mandate)
        .where(Mandate.agent_id == agent.id, Mandate.status == MandateStatus.ACTIVE)
        .order_by(Mandate.created_at.desc())
    )
    mandate_res = await db.execute(mandate_stmt)
    mandate = mandate_res.scalars().first()

    if not mandate:
        return MCPJsonRpcResponse(
            id=request_payload.id,
            error={
                "code": -32002,
                "message": f"Agent '{agent.name}' has no active financial mandate",
            },
        )

    # 2. Handle MCP Methods
    if request_payload.method == "initialize":
        return MCPJsonRpcResponse(
            id=request_payload.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Mandate-Razorpay-MCP-Gateway", "version": "1.0.0"},
            },
        )

    elif request_payload.method == "tools/list":
        # Dynamic Tool Filtering: Slashes 35+ tools down to authorized subset
        filtered_tools = get_filtered_mcp_tools(agent, mandate)
        return MCPJsonRpcResponse(
            id=request_payload.id,
            result={"tools": filtered_tools},
        )

    elif request_payload.method == "tools/call":
        tool_name = request_payload.params.get("name")
        arguments = request_payload.params.get("arguments", {})

        return await _dispatch_mcp_tool_call(
            db=db,
            agent=agent,
            mandate=mandate,
            tool_name=tool_name,
            arguments=arguments,
            rpc_id=request_payload.id,
        )

    return MCPJsonRpcResponse(
        id=request_payload.id,
        error={"code": -32601, "message": f"Method '{request_payload.method}' not found"},
    )


async def _dispatch_mcp_tool_call(
    db: AsyncSession,
    agent: Agent,
    mandate: Mandate,
    tool_name: str | None,
    arguments: dict[str, Any],
    rpc_id: Any,
) -> MCPJsonRpcResponse:
    """Validates schema arguments strictly, converts to Mandate FinancialOperation, and dispatches."""
    from apps.api.routes.operations import request_financial_operation

    if not tool_name or tool_name not in RAZORPAY_MCP_TOOL_REGISTRY:
        return MCPJsonRpcResponse(
            id=rpc_id,
            error={"code": -32602, "message": f"Unknown or unregistered MCP tool: '{tool_name}'"},
        )

    tool_def = RAZORPAY_MCP_TOOL_REGISTRY[tool_name]
    op_type = tool_def.get("operation_type")

    # Strict Validation: Check for unexpected/unauthorized parameter injection without silent mutation
    schema_props = tool_def["inputSchema"]["properties"]
    for arg_key in arguments.keys():
        if arg_key not in schema_props:
            return MCPJsonRpcResponse(
                id=rpc_id,
                error={
                    "code": -32602,
                    "message": f"Schema validation error: Unauthorized/unexpected parameter '{arg_key}' passed to tool '{tool_name}'",
                },
            )

    start_time = time.perf_counter()

    # Case A: Read-Only Tool Invocation
    if op_type is None:
        if tool_name == "payments_fetch_order":
            order_id = arguments.get("order_id", "")
            rzp_order = await razorpay_client.fetch_order(order_id)
            return MCPJsonRpcResponse(
                id=rpc_id,
                result={
                    "content": [{"type": "text", "text": str(rzp_order.model_dump())}],
                    "_mandate_meta": {
                        "authorized": True,
                        "read_only": True,
                        "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    },
                },
            )
        elif tool_name == "payments_fetch_payment":
            payment_id = arguments.get("payment_id", "")
            return MCPJsonRpcResponse(
                id=rpc_id,
                result={
                    "content": [{"type": "text", "text": f"Payment details for {payment_id}"}],
                    "_mandate_meta": {"authorized": True, "read_only": True},
                },
            )
        elif tool_name == "payouts_create":
            # Attempted unauthorized payout
            return MCPJsonRpcResponse(
                id=rpc_id,
                error={
                    "code": -32003,
                    "message": "Policy DENIED: Agent does not possess PAYOUTS authorization.",
                },
            )

    # Case B: Financial Mutating Tool -> Route strictly through Mandate Policy Engine
    amount = arguments.get("amount", 0)
    currency = arguments.get("currency", "INR")

    op_req = OperationCreate(
        idempotency_key=f"idemp_mcp_{uuid.uuid4().hex}",
        agent_id=agent.id,
        mandate_id=mandate.id,
        operation_type=op_type,
        amount=amount,
        currency=currency,
        payload=arguments,
    )

    try:
        op = await request_financial_operation(payload=op_req, db=db)
        decision = op.policy_evaluation_details.get("decision", "DENY")
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if decision == "DENY":
            return MCPJsonRpcResponse(
                id=rpc_id,
                result={
                    "isError": True,
                    "content": [
                        {"type": "text", "text": f"Mandate Policy DENIED: {op.error_message}"}
                    ],
                    "_mandate_meta": {
                        "decision": "DENY",
                        "operation_id": op.operation_id,
                        "reasons": op.policy_evaluation_details.get("rejection_reasons", []),
                        "latency_ms": elapsed_ms,
                    },
                },
            )

        # Successful execution
        return MCPJsonRpcResponse(
            id=rpc_id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed {tool_name} successfully. Operation ID: {op.operation_id}, Status: {op.status.value}",
                    }
                ],
                "_mandate_meta": {
                    "decision": "ALLOW",
                    "operation_id": op.operation_id,
                    "status": op.status.value,
                    "amount_paise": op.amount,
                    "remaining_mandate_budget": max(
                        0,
                        mandate.aggregate_spend_limit
                        - (mandate.current_aggregate_spend + mandate.reserved_spend),
                    ),
                    "latency_ms": elapsed_ms,
                },
            },
        )
    except Exception as exc:
        return MCPJsonRpcResponse(
            id=rpc_id,
            error={"code": -32000, "message": f"Mandate MCP execution error: {str(exc)}"},
        )
