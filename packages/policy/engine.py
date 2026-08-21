"""Deterministic Policy Engine with structured ALLOW/DENY/REQUIRE_HUMAN_REVIEW evaluations."""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from packages.core.enums import AgentStatus, MandateStatus, PolicyDecisionType
from packages.core.models import Agent, FinancialOperation, Mandate


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware in UTC for safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PolicyRuleDiagnostic(BaseModel):
    """Evaluation result for an individual policy rule."""
    model_config = ConfigDict(from_attributes=True)

    rule_name: str
    decision: PolicyDecisionType
    passed: bool
    reason: str
    latency_ms: float
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    """Comprehensive policy engine evaluation decision output."""
    model_config = ConfigDict(from_attributes=True)

    decision: PolicyDecisionType
    approved: bool
    requires_human_review: bool
    operation_id: str
    agent_id: str
    mandate_id: str
    total_latency_ms: float
    rejection_reasons: List[str] = Field(default_factory=list)
    review_reasons: List[str] = Field(default_factory=list)
    rule_diagnostics: List[PolicyRuleDiagnostic] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyRule(ABC):
    """Abstract base class for all deterministic mandate policy rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        pass


class AgentStatusRule(PolicyRule):
    """Verifies that the calling AI Agent identity is ACTIVE."""

    @property
    def name(self) -> str:
        return "AGENT_STATUS_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        if agent.status != AgentStatus.ACTIVE:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Agent '{agent.id}' is in status {agent.status.value}; must be ACTIVE",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"agent_status": agent.status.value},
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Agent is active and verified",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class MandateLifecycleRule(PolicyRule):
    """Verifies that the mandate is ACTIVE and within its valid time-window."""

    @property
    def name(self) -> str:
        return "MANDATE_LIFECYCLE_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        now = datetime.now(timezone.utc)

        if mandate.status != MandateStatus.ACTIVE:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Mandate status is {mandate.status.value}; expected ACTIVE",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"mandate_status": mandate.status.value},
            )

        valid_from = ensure_utc(mandate.valid_from)
        valid_until = ensure_utc(mandate.valid_until)

        if valid_from and now < valid_from:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Mandate is not yet effective (valid from {valid_from.isoformat()})",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
            )

        if valid_until and now > valid_until:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Mandate has expired (valid until {valid_until.isoformat()})",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
            )

        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Mandate is active and within validity window",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class CurrencyMatchRule(PolicyRule):
    """Verifies that the requested financial currency matches the mandate constraint."""

    @property
    def name(self) -> str:
        return "CURRENCY_MATCH_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        if operation.currency.upper() != mandate.currency.upper():
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Requested currency '{operation.currency}' does not match mandate bound '{mandate.currency}'",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"requested_currency": operation.currency, "mandate_currency": mandate.currency},
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Currency restriction satisfied",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class AllowedOperationTypeRule(PolicyRule):
    """Verifies that the requested operation type is explicitly whitelisted."""

    @property
    def name(self) -> str:
        return "OPERATION_TYPE_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        op_type = operation.operation_type.value if hasattr(operation.operation_type, "value") else str(operation.operation_type)
        if mandate.allowed_operations and op_type not in mandate.allowed_operations:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Operation type '{op_type}' is not authorized in mandate whitelist",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"allowed_operations": mandate.allowed_operations, "requested": op_type},
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason=f"Operation type '{op_type}' is authorized",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class PerTransactionLimitRule(PolicyRule):
    """Enforces single-operation maximum amount bounds."""

    @property
    def name(self) -> str:
        return "PER_TRANSACTION_LIMIT_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        if operation.amount > mandate.max_amount_per_op:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Requested amount {operation.amount} exceeds per-transaction limit {mandate.max_amount_per_op}",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"requested_amount": operation.amount, "limit": mandate.max_amount_per_op},
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Amount is within per-transaction ceiling",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class AggregateSpendLimitRule(PolicyRule):
    """Enforces aggregate spending limits including committed and active reservations."""

    @property
    def name(self) -> str:
        return "AGGREGATE_SPEND_LIMIT_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        reserved = getattr(mandate, "reserved_spend", 0)
        current = getattr(mandate, "current_aggregate_spend", 0)
        projected_total = current + reserved + operation.amount
        if projected_total > mandate.aggregate_spend_limit:
            remaining = max(0, mandate.aggregate_spend_limit - (current + reserved))
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Operation amount {operation.amount} exceeds remaining aggregate mandate budget ({remaining})",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={
                    "committed_spend": current,
                    "reserved_spend": reserved,
                    "aggregate_limit": mandate.aggregate_spend_limit,
                    "remaining_budget": remaining,
                },
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Aggregate spend budget available",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class HumanReviewThresholdRule(PolicyRule):
    """Triggers REQUIRE_HUMAN_REVIEW when operation exceeds sensitive approval threshold."""

    @property
    def name(self) -> str:
        return "HUMAN_REVIEW_THRESHOLD_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        if getattr(operation, "approved_by_id", None):
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.ALLOW,
                passed=True,
                reason=f"Human signoff granted by principal '{operation.approved_by_id}'",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
            )

        threshold = getattr(mandate, "review_threshold_amount", None)
        if threshold and operation.amount >= threshold:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.REQUIRE_HUMAN_REVIEW,
                passed=False,
                reason=f"Operation amount {operation.amount} reaches review threshold {threshold}",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={"amount": operation.amount, "threshold": threshold},
            )

        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Under human review threshold",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class PolicyEngine:
    """Deterministic policy pipeline orchestrating all mandate verification rules."""

    def __init__(self, rules: Optional[List[PolicyRule]] = None) -> None:
        self.rules: List[PolicyRule] = rules or [
            AgentStatusRule(),
            MandateLifecycleRule(),
            CurrencyMatchRule(),
            AllowedOperationTypeRule(),
            PerTransactionLimitRule(),
            AggregateSpendLimitRule(),
            HumanReviewThresholdRule(),
        ]

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        start_time = time.perf_counter()
        diagnostics: List[PolicyRuleDiagnostic] = []
        rejection_reasons: List[str] = []
        review_reasons: List[str] = []

        final_decision = PolicyDecisionType.ALLOW

        for rule in self.rules:
            diag = await rule.evaluate(agent, mandate, operation, context)
            diagnostics.append(diag)

            if diag.decision == PolicyDecisionType.DENY:
                rejection_reasons.append(f"[{diag.rule_name}] {diag.reason}")
                final_decision = PolicyDecisionType.DENY
            elif diag.decision == PolicyDecisionType.REQUIRE_HUMAN_REVIEW and final_decision != PolicyDecisionType.DENY:
                review_reasons.append(f"[{diag.rule_name}] {diag.reason}")
                final_decision = PolicyDecisionType.REQUIRE_HUMAN_REVIEW

        total_latency = round((time.perf_counter() - start_time) * 1000, 3)

        return PolicyEvaluationResult(
            decision=final_decision,
            approved=(final_decision == PolicyDecisionType.ALLOW),
            requires_human_review=(final_decision == PolicyDecisionType.REQUIRE_HUMAN_REVIEW),
            operation_id=operation.operation_id,
            agent_id=agent.id,
            mandate_id=mandate.id,
            total_latency_ms=total_latency,
            rejection_reasons=rejection_reasons,
            review_reasons=review_reasons,
            rule_diagnostics=diagnostics,
        )
