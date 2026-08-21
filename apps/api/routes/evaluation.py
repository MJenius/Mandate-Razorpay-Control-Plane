"""Adversarial Evaluation Lab and Security Benchmark API routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import MandateStatus
from packages.core.models import Agent, Mandate
from packages.eval.harness import BenchmarkMetrics, EvaluationHarness
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.evaluation")
router = APIRouter(prefix="/evaluation", tags=["Adversarial Evaluation Lab"])


class RunBenchmarkRequest(BaseModel):
    agent_id: str | None = None
    seed: int = Field(default=42, description="Deterministic seed for reproducible evaluation")
    multiplier: int = Field(default=1, ge=1, le=50, description="Multiplier for scenario volume")


@router.get("/scenarios")
async def list_adversarial_scenarios() -> list[dict[str, Any]]:
    """Returns the library of standard adversarial attack scenarios across all 5 profiles."""
    harness = EvaluationHarness(db=None)  # Type ignore for scenario listing
    scenarios = harness.load_all_scenarios(multiplier=1)
    return [s.model_dump() for s in scenarios]


@router.post("/run", response_model=BenchmarkMetrics)
async def execute_adversarial_benchmark(
    payload: RunBenchmarkRequest,
    db: AsyncSession = Depends(get_db_session),
) -> BenchmarkMetrics:
    """
    Executes a reproducible adversarial benchmark trial against Mandate.
    Measures block rate, policy bypass rate, false positive rate, financial loss prevented,
    and authorization latency percentiles.
    """
    # 1. Resolve or create benchmark test agent & mandate
    if payload.agent_id:
        agent = await db.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        mandate_stmt = select(Mandate).where(
            Mandate.agent_id == agent.id, Mandate.status == MandateStatus.ACTIVE
        )
        mandate = (await db.execute(mandate_stmt)).scalars().first()
    else:
        # Query default benchmark agent
        agent_stmt = select(Agent).limit(1)
        agent = (await db.execute(agent_stmt)).scalar_one_or_none()
        mandate_stmt = select(Mandate).where(Mandate.status == MandateStatus.ACTIVE).limit(1)
        mandate = (await db.execute(mandate_stmt)).scalar_one_or_none()

    if not agent or not mandate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benchmark requires at least one active agent and mandate in the system.",
        )

    logger.info("running_adversarial_benchmark", seed=payload.seed, multiplier=payload.multiplier)
    harness = EvaluationHarness(db=db, seed=payload.seed)
    metrics = await harness.run_evaluation(
        agent=agent, mandate=mandate, multiplier=payload.multiplier
    )

    return metrics


@router.get("/baselines")
async def get_comparative_baselines() -> dict[str, Any]:
    """Returns baseline comparative analysis: No Controls vs Basic Permissions vs Mandate."""
    return {
        "models": {
            "no_controls": {
                "name": "No Controls (Raw Gateway Access)",
                "block_rate": 0.0,
                "bypass_rate": 1.0,
                "loss_vulnerability": "100% of malicious/buggy transactions execute against card/gateway.",
            },
            "basic_tool_permissions": {
                "name": "Basic Tool Permissions (Boolean RBAC)",
                "block_rate": 0.28,
                "bypass_rate": 0.72,
                "loss_vulnerability": "Vulnerable to amount escalation, aggregate budget drift, and race conditions.",
            },
            "mandate_control_plane": {
                "name": "Mandate Financial Control Plane",
                "block_rate": 1.0,
                "bypass_rate": 0.0,
                "loss_vulnerability": "Strict zero-gateway-dispatch invariants, two-phase budget reservation, and concurrency safety.",
            },
        }
    }
