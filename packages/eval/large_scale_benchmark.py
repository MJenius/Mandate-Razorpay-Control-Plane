"""Large-scale reproducible benchmark runner executing 1,000 empirical scenarios."""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from packages.core.enums import AgentStatus, MandateStatus, PrincipalRole
from packages.core.models import Agent, Base, Mandate, Principal
from packages.eval.harness import BenchmarkMetrics, EvaluationHarness
from packages.shared.logging import get_logger

logger = get_logger("eval.large_scale")


async def run_thousand_scenario_benchmark(
    seed: int = 123,
    multiplier: int = 100, # 10 base profiles * 100 multiplier = 1,000 scenarios
) -> BenchmarkMetrics:
    """
    Executes a 1,000-scenario reproducible benchmark evaluating Mandate against:
    - 800 Adversarial attack vectors (Overreaching, Compromised, Buggy, Prompt-Injection, Parameter Spoofing)
    - 200 Legitimate baseline requests (Measuring False Positive Rate and Latency)
    """
    # Configure Razorpay mock mode for local large-scale benchmarking to avoid live gateway rate limits (HTTP 429)
    from apps.api.routes import operations
    operations.razorpay_client.mock_mode = True

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as db:
        # Create deterministic evaluation principal & agent
        principal = Principal(name="Benchmark Enterprise", email=f"bench_{seed}@mandate.dev", role=PrincipalRole.ADMIN)
        db.add(principal)
        await db.flush()

        agent = Agent(
            name="Large Scale Test Agent",
            owner_id=principal.id,
            agent_type="SHOPPING",
            status=AgentStatus.ACTIVE,
            api_key_hash=f"hash_bench_large_{seed}",
        )
        db.add(agent)
        await db.flush()

        # Large aggregate budget (₹50,00,000) so aggregate budget exhaustion is not triggered by legitimate baseline repetitions
        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=2500000, # ₹25,000 per op
            aggregate_spend_limit=500000000, # ₹50,00,000
            allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(mandate)
        await db.commit()

        start_time = time.perf_counter()
        harness = EvaluationHarness(db=db, seed=seed)
        metrics = await harness.run_evaluation(agent=agent, mandate=mandate, multiplier=multiplier)
        total_time = round(time.perf_counter() - start_time, 2)

        print(
            f"\n=======================================================\n"
            f"[EMPIRICAL BENCHMARK RESULT (N={metrics.total_scenarios})]\n"
            f"  - Total Scenarios Evaluated: {metrics.total_scenarios}\n"
            f"  - Hostile Action Block Rate: {metrics.unauthorized_action_block_rate * 100:.1f}%\n"
            f"  - Policy Bypass Rate: {metrics.policy_bypass_rate * 100:.1f}%\n"
            f"  - False Positive Rate (FPR): {metrics.false_positive_rate * 100:.1f}%\n"
            f"  - Legitimate Acceptance Rate: {metrics.legitimate_action_acceptance_rate * 100:.1f}%\n"
            f"  - Counterfactual Loss Prevented: Rs. {metrics.financial_loss_prevented_inr:,.2f}\n"
            f"  - P50 Policy Latency: {metrics.latency_p50_ms} ms\n"
            f"  - P95 Policy Latency: {metrics.latency_p95_ms} ms\n"
            f"  - P99 Policy Latency: {metrics.latency_p99_ms} ms\n"
            f"  - Total Benchmark Wall Time: {total_time}s\n"
            f"=======================================================\n"
        )

        return metrics


if __name__ == "__main__":
    metrics_result = asyncio.run(run_thousand_scenario_benchmark())
