"""Prometheus metrics registry and OpenTelemetry tracing abstraction for Mandate Control Plane."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# 1. Prometheus Metrics Definitions (Specific to Financial Control Plane & Correctness)
AUTH_DECISIONS_TOTAL = Counter(
    "mandate_authorization_decisions_total",
    "Total deterministic authorization decisions evaluated",
    ["decision", "operation_type", "agent_id"],
)

POLICY_RULE_EVALUATIONS_TOTAL = Counter(
    "mandate_policy_rule_evaluations_total",
    "Total policy rule evaluations by status and rule name",
    ["rule_name", "decision", "passed"],
)

POLICY_EVALUATION_LATENCY_SECONDS = Histogram(
    "mandate_policy_evaluation_duration_seconds",
    "Latency of deterministic policy engine evaluations in seconds",
    buckets=[0.001, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0],
)

CAS_BUDGET_RESERVATIONS_TOTAL = Counter(
    "mandate_cas_budget_reservations_total",
    "Total atomic CAS budget reservations attempted",
    ["status"],  # "success", "conflict_retry", "exhausted"
)

CAS_CONFLICT_RETRIES_TOTAL = Counter(
    "mandate_cas_conflict_retries_total",
    "Total CAS concurrency conflict retries executed",
)

FINANCIAL_STATE_TRANSITIONS_TOTAL = Counter(
    "mandate_financial_state_transitions_total",
    "Financial state machine transitions executed",
    ["from_state", "to_state", "status"],
)

RATE_LIMIT_REJECTIONS_TOTAL = Counter(
    "mandate_rate_limit_rejections_total",
    "Total rate limit rejections intercepted at boundary",
    ["agent_id", "tier"],
)

WEBHOOK_INGESTION_TOTAL = Counter(
    "mandate_webhook_events_total",
    "Total Razorpay webhook events ingested",
    ["event_type", "status"],  # "processed", "duplicate_ignored", "signature_failed", "dlq"
)

RECONCILIATION_SWEEPS_TOTAL = Counter(
    "mandate_reconciliation_sweeps_total",
    "Total background ledger reconciliation sweeps completed",
)

RECONCILIATION_DISCREPANCIES_DETECTED = Counter(
    "mandate_reconciliation_discrepancies_total",
    "Total discrepancies detected during read-only gateway reconciliation",
    ["type"],
)

ACTIVE_BUDGET_RESERVATIONS_GAUGE = Gauge(
    "mandate_active_budget_reservations_paise",
    "Currently reserved uncommitted spend in paise across active mandates",
)

INVARIANT_VIOLATIONS_TOTAL = Counter(
    "mandate_invariant_violations_total",
    "Critical financial invariant violations (MUST ALWAYS BE ZERO)",
    ["invariant_name"],
)


def get_prometheus_metrics_bytes() -> tuple[bytes, str]:
    """Renders all Prometheus metrics in the latest standard text exposition format."""
    return generate_latest(), CONTENT_TYPE_LATEST


class OpenTelemetryTraceSpan:
    """Lightweight deterministic OpenTelemetry-compatible span wrapper for tracing control plane flow."""

    def __init__(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.name = name
        self.attributes = attributes or {}
        self.start_time_ns = 0
        self.duration_ms = 0.0

    def __enter__(self) -> "OpenTelemetryTraceSpan":
        self.start_time_ns = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed_ns = time.perf_counter_ns() - self.start_time_ns
        self.duration_ms = round(elapsed_ns / 1_000_000.0, 3)
        if exc_val:
            self.attributes["error"] = True
            self.attributes["error_message"] = str(exc_val)


@asynccontextmanager
async def trace_span(name: str, attributes: dict[str, Any] | None = None) -> AsyncGenerator[OpenTelemetryTraceSpan, None]:
    span = OpenTelemetryTraceSpan(name, attributes)
    span.start_time_ns = time.perf_counter_ns()
    try:
        yield span
    except Exception as e:
        span.attributes["error"] = True
        span.attributes["error_message"] = str(e)
        raise
    finally:
        elapsed_ns = time.perf_counter_ns() - span.start_time_ns
        span.duration_ms = round(elapsed_ns / 1_000_000.0, 3)
