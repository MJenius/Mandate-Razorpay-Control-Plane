import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.agents.adapter import BaseLLMAdapter, get_llm_adapter
from packages.agents.runner import AgentRunner
from packages.core.enums import MandateStatus
from packages.core.models import Agent, AgentExecutionTrace, Mandate
from packages.shared.auth import authenticate_agent_caller
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.agent_chat")
router = APIRouter(prefix="/agents", tags=["Agent Chat & Traces"])

# Default adapter (can be overridden in tests)
default_llm_adapter: BaseLLMAdapter | None = None


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2048)
    session_id: str | None = None
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls: list[dict[str, Any]]
    policy_decisions: list[dict[str, Any]]
    operation_ids: list[str]
    latency_ms: float


class AgentTraceResponse(BaseModel):
    id: str
    session_id: str
    agent_id: str
    user_prompt: str
    model_provider: str
    model_name: str
    tool_name: str | None = None
    tool_arguments: dict[str, Any]
    tool_result: dict[str, Any]
    operation_id: str | None = None
    policy_decision: str | None = None
    latency_ms: float
    created_at: Any


@router.post("/{agent_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    agent_id: str,
    payload: AgentChatRequest,
    x_agent_key: str | None = Header(None, alias="X-Agent-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Direct natural language dialogue with an autonomous agent.
    The agent uses tool calling to request financial operations, which are intercepted
    and authorized strictly by Mandate's Deterministic Policy Engine.
    """
    if x_agent_key or authorization:
        agent = await authenticate_agent_caller(
            db=db,
            x_agent_key=x_agent_key,
            authorization=authorization,
            x_agent_id=agent_id,
            required=True,
        )
    else:
        agent = await db.get(Agent, agent_id)

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")



    # Find the active mandate for this agent
    mandate_stmt = (
        select(Mandate)
        .where(Mandate.agent_id == agent.id, Mandate.status == MandateStatus.ACTIVE)
        .order_by(Mandate.created_at.desc())
    )
    mandate_res = await db.execute(mandate_stmt)
    mandate = mandate_res.scalars().first()

    if not mandate:
        # Check if agent had a previous revoked/suspended mandate (e.g. after Step 5 demo revocation)
        # and auto-reissue a fresh active demo mandate so conversational playground remains interactive.
        prev_mandate_stmt = (
            select(Mandate)
            .where(Mandate.agent_id == agent.id)
            .order_by(Mandate.created_at.desc())
        )
        prev_mandate = (await db.execute(prev_mandate_stmt)).scalars().first()

        logger.info("reissuing_active_mandate_for_interactive_agent", agent_id=agent.id)
        if agent.agent_type.upper() == "SUPPORT":
            max_op = 500000  # ₹5,000
            agg_limit = 2500000  # ₹25,000
            allowed_ops = ["CREATE_REFUND"]
        elif agent.agent_type.upper() == "SHOPPING":
            max_op = 2500000  # ₹25,000
            agg_limit = 10000000  # ₹1,00,000
            allowed_ops = ["CREATE_ORDER", "CREATE_PAYMENT_LINK"]
        else:  # PROCUREMENT or default
            max_op = 1000000  # ₹10,000
            agg_limit = 1500000  # ₹15,000
            allowed_ops = ["CREATE_ORDER"]

        mandate = Mandate(
            id=f"mnd_{agent.agent_type.lower()}_{uuid.uuid4().hex[:8]}",
            agent_id=agent.id,
            granted_by_id=agent.owner_id,
            delegation_depth=0 if not prev_mandate else prev_mandate.delegation_depth,
            currency="INR",
            max_amount_per_op=max_op,
            aggregate_spend_limit=agg_limit,
            allowed_operations=allowed_ops,
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(mandate)
        await db.flush()

    adapter = default_llm_adapter or get_llm_adapter()
    runner = AgentRunner(db=db, adapter=adapter)
    result = await runner.execute_turn(
        agent=agent,
        mandate=mandate,
        user_prompt=payload.message,
        session_id=payload.session_id,
        conversation_history=payload.conversation_history,
    )

    return result.to_dict()


@router.get("/{agent_id}/traces", response_model=list[AgentTraceResponse])
async def list_agent_traces(
    agent_id: str,
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentExecutionTrace]:
    """Retrieve structured tool call execution traces and Mandate policy decisions."""
    stmt = (
        select(AgentExecutionTrace)
        .where(AgentExecutionTrace.agent_id == agent_id)
        .order_by(AgentExecutionTrace.created_at.desc())
        .limit(limit)
    )
    if session_id:
        stmt = stmt.where(AgentExecutionTrace.session_id == session_id)

    res = await db.execute(stmt)
    return list(res.scalars().all())
