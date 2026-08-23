#!/usr/bin/env python3
"""PostgreSQL-only contention benchmark for Mandate's conditional budget reservation."""

import argparse
import asyncio
import csv
import json
import platform
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.core.concurrency import reserve_budget
from packages.core.enums import OperationStatus, OperationType, PrincipalRole
from packages.core.models import Agent, FinancialOperation, Mandate, Principal, Transaction
from packages.shared.database import get_engine

AMOUNT = 100


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, round((len(ordered) - 1) * q)))] if ordered else 0.0


async def run_trial(
    sessions: async_sessionmaker[AsyncSession], workload: str, concurrency: int
) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    async with sessions() as db:
        principal = Principal(name=f"benchmark-{run_id}", email=f"{run_id}@benchmark.local", role=PrincipalRole.ADMIN)
        db.add(principal)
        await db.flush()
        agent = Agent(name=f"benchmark-{run_id}", owner_id=principal.id, api_key_hash=f"benchmark-{run_id}")
        db.add(agent)
        await db.flush()
        mandates = [
            Mandate(
                agent_id=agent.id, granted_by_id=principal.id, currency="INR", max_amount_per_op=AMOUNT,
                aggregate_spend_limit=AMOUNT if workload == "low_contention" else AMOUNT * (concurrency // 2),
                allowed_operations=[OperationType.CREATE_ORDER.value], valid_until=datetime.now(UTC) + timedelta(hours=1),
            )
            for _ in range(concurrency if workload == "low_contention" else 1)
        ]
        db.add_all(mandates)
        await db.commit()
        mandate_ids = [mandate.id for mandate in mandates]

    latencies: list[float] = []

    async def attempt(index: int) -> bool:
        started = time.perf_counter()
        async with sessions() as db:
            mandate_id = mandate_ids[index] if workload == "low_contention" else mandate_ids[0]
            operation = FinancialOperation(
                operation_id=f"bench_{run_id}_{index}", idempotency_key=f"bench_{run_id}_{index}",
                agent_id=agent.id, mandate_id=mandate_id, operation_type=OperationType.CREATE_ORDER,
                status=OperationStatus.INITIATED, amount=AMOUNT, currency="INR",
            )
            db.add(operation)
            reserved = await reserve_budget(db, mandate_id, AMOUNT)
            operation.status = OperationStatus.RESERVED if reserved else OperationStatus.POLICY_REJECTED
            await db.commit()
        latencies.append((time.perf_counter() - started) * 1000)
        return reserved

    started = time.perf_counter()
    outcomes = await asyncio.gather(*(attempt(index) for index in range(concurrency)), return_exceptions=True)
    duration_ms = (time.perf_counter() - started) * 1000
    failures = sum(isinstance(outcome, Exception) for outcome in outcomes)
    successes = sum(outcome is True for outcome in outcomes)
    rejections = sum(outcome is False for outcome in outcomes)

    async with sessions() as db:
        rows = (await db.execute(select(Mandate).where(Mandate.id.in_(mandate_ids)))).scalars().all()
        committed = sum(row.current_aggregate_spend for row in rows)
        reserved = sum(row.reserved_spend for row in rows)
        limit = sum(row.aggregate_spend_limit for row in rows)
        operations = await db.scalar(select(func.count()).select_from(FinancialOperation).where(FinancialOperation.operation_id.like(f"bench_{run_id}_%")))
        ledger_entries = await db.scalar(select(func.count()).select_from(Transaction).join(FinancialOperation).where(FinancialOperation.operation_id.like(f"bench_{run_id}_%")))
        await db.execute(delete(FinancialOperation).where(FinancialOperation.operation_id.like(f"bench_{run_id}_%")))
        await db.execute(delete(Mandate).where(Mandate.id.in_(mandate_ids)))
        await db.execute(delete(Agent).where(Agent.id == agent.id))
        await db.execute(delete(Principal).where(Principal.id == principal.id))
        await db.commit()

    overspend = max(0, committed + reserved - limit)
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(), "run_id": run_id, "workload": workload,
        "concurrency": concurrency, "total_operations": concurrency, "successful_reservations": successes,
        "rejected_reservations": rejections, "failed_operations": failures, "cas_conflicts": rejections,
        "cas_retries": 0, "p50_latency_ms": round(percentile(latencies, 0.50), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3), "p99_latency_ms": round(percentile(latencies, 0.99), 3),
        "duration_ms": round(duration_ms, 3), "success_rate": round(successes / concurrency, 6),
        "error_rate": round(failures / concurrency, 6), "final_committed_spend": committed,
        "final_reserved_spend": reserved, "mandate_limit": limit, "operation_rows": operations or 0,
        "ledger_entries": ledger_entries or 0, "overspend_amount": overspend,
        "overspend_count": int(overspend > 0), "invariant": "PASS — ZERO OVERSPEND" if overspend == 0 and failures == 0 else "FAIL — FINANCIAL INVARIANT VIOLATED",
    }


async def main_async(args: argparse.Namespace) -> list[dict[str, Any]]:
    engine = get_engine()
    engine.echo = False
    if engine.url.get_backend_name() != "postgresql":
        raise RuntimeError("This benchmark requires PostgreSQL; SQLite is intentionally rejected.")
    sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    results = []
    for workload in ("low_contention", "high_contention"):
        for concurrency in args.concurrency:
            for trial in range(1, args.trials + 1):
                result = await run_trial(sessions, workload, concurrency)
                result["trial"] = trial
                results.append(result)
                print(f"{workload} c={concurrency} trial={trial}: {result['invariant']} p95={result['p95_latency_ms']}ms")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", default="100,200,500", type=lambda value: [int(item) for item in value.split(",")])
    parser.add_argument("--trials", default=3, type=int)
    parser.add_argument("--output-dir", default="benchmarks/results")
    args = parser.parse_args()
    results = asyncio.run(main_async(args))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata = {"timestamp_utc": datetime.now(UTC).isoformat(), "python": sys.version, "platform": platform.platform(), "database": "PostgreSQL via DATABASE_URL", "trials": args.trials, "amount_paise": AMOUNT, "results": results}
    (output / f"concurrency-{stamp}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    with (output / f"concurrency-{stamp}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    if any(result["invariant"].startswith("FAIL") for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
