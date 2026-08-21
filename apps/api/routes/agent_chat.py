"""Agent Chat, Execution Traces, and Autonomous Interaction API routes."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.agents.adapter import BaseLLMAdapter, get_llm_adapter
from packages.agents.runner import AgentRunner
from packages.core.enums import MandateStatus
from packages.core.models import Agent, AgentExecutionTrace, Mandate
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.agent_chat")
router = APIRouter(prefix="/agents", tags=["Agent Chat & Traces"])

# Default adapter (can be overridden in tests)
default_llm_adapter: Optional[BaseLLMAdapter] = None


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2048)
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls: List[Dict[str, Any]]
    policy_decisions: List[Dict[str, Any]]
    operation_ids: List[str]
    latency_ms: float


class AgentTraceResponse(BaseModel):
    id: str
    session_id: str
    agent_id: str
    user_prompt: str
    model_provider: str
    model_name: str
    tool_name: Optional[str] = None
    tool_arguments: Dict[str, Any]
    tool_result: Dict[str, Any]
    operation_id: Optional[str] = None
    policy_decision: Optional[str] = None
    latency_ms: float
    created_at: Any


@router.post("/{agent_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    agent_id: str,
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Direct natural language dialogue with an autonomous agent.
    The agent uses tool calling to request financial operations, which are intercepted
    and authorized strictly by Mandate's Deterministic Policy Engine.
    """
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent.name}' has no active financial mandate",
        )

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


@router.get("/{agent_id}/traces", response_model=List[AgentTraceResponse])
async def list_agent_traces(
    agent_id: str,
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> List[AgentExecutionTrace]:
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
