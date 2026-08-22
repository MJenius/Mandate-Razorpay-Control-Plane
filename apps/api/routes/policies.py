"""Policy Engine inspection, rule registry, and dry-run evaluation API routes."""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import MandateStatus, OperationType
from packages.core.models import Agent, FinancialOperation, Mandate
from packages.policy.engine import PolicyEngine
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.policies")
router = APIRouter(prefix="/policies", tags=["Deterministic Policy Engine"])

policy_engine = PolicyEngine()

POLICY_RULES_METADATA = [
    {
        "name": "AGENT_STATUS_CHECK",
        "order": 1,
        "category": "Identity & Agent Verification",
        "invariant": "Agent must have ACTIVE status in registry",
        "description": "Verifies that the invoking AI Agent is officially registered, has not been suspended, and holds ACTIVE operational status.",
        "enforcement": "Strict Pre-Flight Gate",
    },
    {
        "name": "MANDATE_LIFECYCLE_CHECK",
        "order": 2,
        "category": "Temporal & Lifecycle Validity",
        "invariant": "Mandate must be ACTIVE and valid_from <= now <= valid_until",
        "description": "Verifies that the financial mandate is in ACTIVE status and the current UTC execution timestamp falls strictly within the effective and expiration window.",
        "enforcement": "Deterministic Lifecycle Gate",
    },
    {
        "name": "HIERARCHICAL_DELEGATION_CHECK",
        "order": 3,
        "category": "Hierarchical Delegation & Cascade",
        "invariant": "All ancestor parent mandates in the tree must remain ACTIVE",
        "description": "Recursively traverses up the delegation DAG to verify every parent/ancestor mandate. If any ancestor is suspended or revoked, child authority is immediately invalidated.",
        "enforcement": "Recursive Tree Validation",
    },
    {
        "name": "CURRENCY_MATCH_CHECK",
        "order": 4,
        "category": "Financial Bounds & Boundary Protection",
        "invariant": "Requested currency must exactly match mandate bound (e.g. INR)",
        "description": "Ensures foreign currency conversion attempts or currency tampering cannot bypass bounded INR limits.",
        "enforcement": "Strict Currency Match",
    },
    {
        "name": "OPERATION_TYPE_CHECK",
        "order": 5,
        "category": "Role-Based Capability & Allowlist",
        "invariant": "Requested operation must exist in mandate.allowed_operations whitelist",
        "description": "Strict whitelist verification. For example, prevents shopping agents from initiating refunds (CREATE_REFUND) or merchant payment links unless explicitly granted.",
        "enforcement": "Operation Whitelist Filter",
    },
    {
        "name": "PER_TRANSACTION_LIMIT_CHECK",
        "order": 6,
        "category": "Single-Transaction Ceilings",
        "invariant": "Operation amount <= mandate.max_amount_per_op",
        "description": "Enforces a strict mathematical ceiling per individual transaction (e.g. ₹25,000 for primary shopping, ₹10,000 for procurement sub-agent).",
        "enforcement": "Deterministic Mathematical Ceiling",
    },
    {
        "name": "AGGREGATE_SPEND_LIMIT_CHECK",
        "order": 7,
        "category": "Aggregate Budget & Concurrency CAS",
        "invariant": "current_aggregate_spend + reserved_spend + amount <= aggregate_spend_limit",
        "description": "Enforces global budget limits across all historical and pending operations. Evaluated atomically before two-phase CAS reservation.",
        "enforcement": "Atomic Two-Phase Budget Gate",
    },
    {
        "name": "HUMAN_REVIEW_THRESHOLD_CHECK",
        "order": 8,
        "category": "Human-in-the-Loop Thresholds",
        "invariant": "Operations >= review_threshold_amount require human approval",
        "description": "Flags high-value or unusual operations for explicit human principal sign-off (REQUIRE_HUMAN_REVIEW) before gateway dispatch.",
        "enforcement": "Human Review Routing",
    },
]


class PolicyTestRequest(BaseModel):
    agent_id: str
    mandate_id: str
    operation_type: OperationType = OperationType.CREATE_ORDER
    amount: int = Field(..., description="Amount in paise (e.g. 650000 for Rs. 6500)")
    currency: str = "INR"
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/rules")
async def list_policy_rules() -> dict[str, Any]:
    """
    Returns the complete list of 8 deterministic Policy Engine rules executed in memory
    for every financial operation before any Razorpay gateway dispatch.
    """
    return {
        "engine": "Mandate Deterministic Policy Engine v2.0",
        "rule_count": len(POLICY_RULES_METADATA),
        "zero_gateway_dispatch_invariant": True,
        "rules": POLICY_RULES_METADATA,
    }


@router.post("/test-evaluate")
async def test_evaluate_policy(
    req: PolicyTestRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Dry-run policy evaluation against the real PolicyEngine without mutating database state.
    Returns individual rule diagnostics, pass/fail status, decision, latency, and reasons.
    """
    agent = await db.get(Agent, req.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{req.agent_id}' not found in registry",
        )

    mandate = await db.get(Mandate, req.mandate_id)
    if not mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mandate '{req.mandate_id}' not found",
        )

    synthetic_op = FinancialOperation(
        operation_id="op_dry_run_test",
        idempotency_key="idemp_dry_run",
        agent_id=agent.id,
        mandate_id=mandate.id,
        operation_type=req.operation_type,
        amount=req.amount,
        currency=req.currency.upper(),
        payload=req.payload,
    )

    eval_result = await policy_engine.evaluate(agent, mandate, synthetic_op, context={"db": db})
    return eval_result.model_dump()
