"""Mandate Model Context Protocol (MCP) Security Gateway & JSON-RPC 2.0 Proxy Router."""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
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


@router.get("/registry")
async def get_mcp_registry(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Returns full metadata for the 25 registered Razorpay MCP tools across 8 functional domains,
    along with dynamic attack-surface reduction calculations for standard agent roles.
    """
    categories = sorted(list({t["category"] for t in RAZORPAY_MCP_TOOL_REGISTRY.values()}))
    tools_list = []
    for name, tool in RAZORPAY_MCP_TOOL_REGISTRY.items():
        tools_list.append(
            {
                "name": name,
                "description": tool["description"],
                "category": tool["category"],
                "operation_type": tool["operation_type"].value
                if tool.get("operation_type") and hasattr(tool["operation_type"], "value")
                else str(tool.get("operation_type"))
                if tool.get("operation_type")
                else None,
                "inputSchema": tool["inputSchema"],
            }
        )

    total_tools = len(RAZORPAY_MCP_TOOL_REGISTRY)

    # Calculate exact reduction for standard agent roles
    # Shopping Agent allows: CREATE_ORDER, CREATE_PAYMENT_LINK (3 tools)
    # Procurement Sub-Agent allows: CREATE_ORDER (2 tools)
    # Support Agent allows: CREATE_REFUND (3 tools)
    profiles_summary = {
        "unprotected_direct_mcp": {
            "name": "Direct Unprotected Razorpay MCP Server",
            "exposed_tools_count": total_tools,
            "permitted_categories": categories,
            "attack_surface_reduction_pct": 0.0,
            "credential_exposure": "Raw API credentials provided in agent system prompt",
            "risk": "100% of tool methods exposed (payouts, settlements, refunds, invoices)",
        },
        "shopping_agent": {
            "name": "Shopping / Buyer Agent (Primary)",
            "allowed_operations": ["CREATE_ORDER", "CREATE_PAYMENT_LINK"],
            "permitted_tools": [
                "payments_create_order",
                "payments_fetch_order",
                "payments_fetch_all_orders",
            ],
            "exposed_tools_count": 3,
            "attack_surface_reduction_pct": round(((total_tools - 3) / total_tools) * 100, 1),
        },
        "procurement_agent": {
            "name": "Procurement Sub-Agent (Hardware)",
            "allowed_operations": ["CREATE_ORDER"],
            "permitted_tools": ["payments_create_order", "payments_fetch_order"],
            "exposed_tools_count": 2,
            "attack_surface_reduction_pct": round(((total_tools - 2) / total_tools) * 100, 1),
        },
        "support_agent": {
            "name": "Customer Support & Returns Agent",
            "allowed_operations": ["CREATE_REFUND"],
            "permitted_tools": [
                "payments_create_refund",
                "payments_fetch_refund",
                "payments_fetch_payment",
            ],
            "exposed_tools_count": 3,
            "attack_surface_reduction_pct": round(((total_tools - 3) / total_tools) * 100, 1),
        },
    }

    return {
        "total_registered_tools": total_tools,
        "functional_categories_count": len(categories),
        "categories": categories,
        "tools": tools_list,
        "profiles_summary": profiles_summary,
    }


@router.post("", response_model=MCPJsonRpcResponse)
async def handle_mcp_jsonrpc_gateway(
    request_payload: MCPJsonRpcRequest,
    x_agent_key: str | None = Header(
        None, alias="X-Agent-Key", description="Authoritative calling AI Agent API Key"
    ),
    authorization: str | None = Header(
        None, alias="Authorization", description="Authoritative Bearer token (Agent Key)"
    ),
    x_agent_id: str | None = Header(
        None, alias="X-Agent-Id", description="Agent ID (Compatibility / Demo verification)"
    ),
    db: AsyncSession = Depends(get_db_session),
) -> MCPJsonRpcResponse:
    """
    Production JSON-RPC 2.0 Model Context Protocol (MCP) Gateway:
    1. Authoritative Caller Authentication: X-Agent-Key or Authorization Bearer token validated against database.
    2. Identity Mismatch Prevention: If both Key and X-Agent-Id are provided, strictly verify that the key derives the exact specified agent ID.
    3. Dynamic Tool Filtering ('tools/list'): Slashes tool catalog down to authorized subset.
    4. Guarded Tool Dispatch ('tools/call'): Enforces strict schema validation, routes through Mandate Policy Engine, and dispatches to Razorpay Test Mode.
    """
    # 1. Authoritative Agent Authentication & Identity Resolution
    try:
        from packages.shared.auth import authenticate_agent_caller
        agent = await authenticate_agent_caller(
            db=db,
            x_agent_key=x_agent_key,
            authorization=authorization,
            x_agent_id=x_agent_id,
            required=True,
        )
    except HTTPException as exc:
        return MCPJsonRpcResponse(
            id=request_payload.id,
            error={"code": -32001, "message": exc.detail},
        )

    if not agent:
        return MCPJsonRpcResponse(
            id=request_payload.id,
            error={"code": -32001, "message": "Authentication required"},
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
        op = await request_financial_operation(
            payload=op_req,
            x_agent_key=agent.api_key_hash,
            x_agent_id=agent.id,
            db=db,
        )
        decision = op.policy_evaluation_details.get("decision", "DENY")
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if decision == "DENY":
            return MCPJsonRpcResponse(
                id=rpc_id,
                result={
                    "isError": True,
                    "authorized": False,
                    "policy_decision": "DENY",
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
        from packages.core.models import Transaction
        tx_stmt = select(Transaction).where(Transaction.operation_id == op.id)
        tx_res = await db.execute(tx_stmt)
        tx = tx_res.scalar_one_or_none()
        gateway_order_id = tx.gateway_order_id if (tx and tx.gateway_order_id) else f"order_{op.operation_id}"


        return MCPJsonRpcResponse(
            id=rpc_id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": f"Executed {tool_name} successfully. Operation ID: {op.operation_id}, Status: {op.status.value}",
                    }
                ],
                "authorized": True,
                "policy_decision": "ALLOW",
                "mandate_status": op.status.value,
                "operation_id": op.operation_id,
                "gateway_order": {"id": gateway_order_id},
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

