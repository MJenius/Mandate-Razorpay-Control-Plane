"""Deterministic failure plans for recovery tests and demo endpoints."""

from dataclasses import dataclass
from enum import StrEnum

from packages.core.enums import OperationStatus


class FailureMode(StrEnum):
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    GATEWAY_5XX = "GATEWAY_5XX"
    DROPPED_WEBHOOK = "DROPPED_WEBHOOK"
    WORKER_CRASH = "WORKER_CRASH"
    REDIS_UNAVAILABLE = "REDIS_UNAVAILABLE"
    DB_CONFLICT = "DB_CONFLICT"


@dataclass(frozen=True)
class RecoveryPlan:
    intermediate_state: OperationStatus
    final_state: OperationStatus
    mechanism: str


RECOVERY_PLANS = {
    FailureMode.GATEWAY_TIMEOUT: RecoveryPlan(OperationStatus.RESERVED, OperationStatus.FAILED, "release reservation"),
    FailureMode.GATEWAY_5XX: RecoveryPlan(OperationStatus.RESERVED, OperationStatus.FAILED, "release reservation"),
    FailureMode.DROPPED_WEBHOOK: RecoveryPlan(OperationStatus.EXECUTING, OperationStatus.SUCCEEDED, "reconciliation"),
    FailureMode.WORKER_CRASH: RecoveryPlan(OperationStatus.RESERVED, OperationStatus.FAILED, "stale sweep"),
    FailureMode.REDIS_UNAVAILABLE: RecoveryPlan(OperationStatus.INITIATED, OperationStatus.POLICY_REJECTED, "production fail-closed"),
    FailureMode.DB_CONFLICT: RecoveryPlan(OperationStatus.INITIATED, OperationStatus.POLICY_REJECTED, "conditional reservation"),
}


def recovery_plan(mode: FailureMode) -> RecoveryPlan:
    return RECOVERY_PLANS[mode]
