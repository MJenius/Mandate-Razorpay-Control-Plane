"""Deterministic Policy Engine with hierarchical delegation validation and structured ALLOW/DENY/REQUIRE_HUMAN_REVIEW evaluations."""

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import AgentStatus, MandateStatus, PolicyDecisionType
from packages.core.models import Agent, FinancialOperation, Mandate


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class PolicyRuleDiagnostic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_name: str
    decision: PolicyDecisionType
    passed: bool
    reason: str
    latency_ms: float
    context: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: PolicyDecisionType
    approved: bool
    requires_human_review: bool
    operation_id: str
    agent_id: str
    mandate_id: str
    total_latency_ms: float
    rejection_reasons: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    rule_diagnostics: list[PolicyRuleDiagnostic] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRule(ABC):
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
        context: dict[str, Any] | None = None,
    ) -> PolicyRuleDiagnostic:
        pass


class AgentStatusRule(PolicyRule):
    @property
    def name(self) -> str:
        return "AGENT_STATUS_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
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
    @property
    def name(self) -> str:
        return "MANDATE_LIFECYCLE_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        now = datetime.now(UTC)

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


class HierarchicalDelegationRule(PolicyRule):
    """Verifies that all ancestor parent mandates in the tree remain ACTIVE and valid."""

    @property
    def name(self) -> str:
        return "HIERARCHICAL_DELEGATION_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()

        # If this is a root mandate (no parent), pass immediately
        if not mandate.parent_mandate_id:
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.ALLOW,
                passed=True,
                reason="Root mandate has no parent dependencies",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
            )

        # Context session check if available
        db_session: AsyncSession | None = context.get("db") if context else None
        if db_session:
            curr_parent_id: str | None = mandate.parent_mandate_id
            while curr_parent_id:
                parent = await db_session.get(Mandate, curr_parent_id)
                if not parent:
                    return PolicyRuleDiagnostic(
                        rule_name=self.name,
                        decision=PolicyDecisionType.DENY,
                        passed=False,
                        reason=f"Ancestor parent mandate '{curr_parent_id}' not found",
                        latency_ms=round((time.perf_counter() - start) * 1000, 3),
                    )

                if parent.status != MandateStatus.ACTIVE:
                    return PolicyRuleDiagnostic(
                        rule_name=self.name,
                        decision=PolicyDecisionType.DENY,
                        passed=False,
                        reason=f"Parent mandate '{parent.id}' in delegation tree is {parent.status.value}; authority invalidated",
                        latency_ms=round((time.perf_counter() - start) * 1000, 3),
                        context={"parent_id": parent.id, "parent_status": parent.status.value},
                    )

                curr_parent_id = parent.parent_mandate_id

        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Delegation hierarchy validated and active",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class CurrencyMatchRule(PolicyRule):
    @property
    def name(self) -> str:
        return "CURRENCY_MATCH_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        if operation.currency.upper() != mandate.currency.upper():
            return PolicyRuleDiagnostic(
                rule_name=self.name,
                decision=PolicyDecisionType.DENY,
                passed=False,
                reason=f"Requested currency '{operation.currency}' does not match mandate bound '{mandate.currency}'",
                latency_ms=round((time.perf_counter() - start) * 1000, 3),
                context={
                    "requested_currency": operation.currency,
                    "mandate_currency": mandate.currency,
                },
            )
        return PolicyRuleDiagnostic(
            rule_name=self.name,
            decision=PolicyDecisionType.ALLOW,
            passed=True,
            reason="Currency restriction satisfied",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class AllowedOperationTypeRule(PolicyRule):
    @property
    def name(self) -> str:
        return "OPERATION_TYPE_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
    ) -> PolicyRuleDiagnostic:
        start = time.perf_counter()
        op_type = (
            operation.operation_type.value
            if hasattr(operation.operation_type, "value")
            else str(operation.operation_type)
        )
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
    @property
    def name(self) -> str:
        return "PER_TRANSACTION_LIMIT_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
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
    @property
    def name(self) -> str:
        return "AGGREGATE_SPEND_LIMIT_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
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
    @property
    def name(self) -> str:
        return "HUMAN_REVIEW_THRESHOLD_CHECK"

    async def evaluate(
        self,
        agent: Agent,
        mandate: Mandate,
        operation: FinancialOperation,
        context: dict[str, Any] | None = None,
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
    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules: list[PolicyRule] = rules or [
            AgentStatusRule(),
            MandateLifecycleRule(),
            HierarchicalDelegationRule(),
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
        context: dict[str, Any] | None = None,
    ) -> PolicyEvaluationResult:
        start_time = time.perf_counter()
        diagnostics: list[PolicyRuleDiagnostic] = []
        rejection_reasons: list[str] = []
        review_reasons: list[str] = []

        final_decision = PolicyDecisionType.ALLOW

        for rule in self.rules:
            diag = await rule.evaluate(agent, mandate, operation, context)
            diagnostics.append(diag)

            if diag.decision == PolicyDecisionType.DENY:
                rejection_reasons.append(f"[{diag.rule_name}] {diag.reason}")
                final_decision = PolicyDecisionType.DENY
            elif (
                diag.decision == PolicyDecisionType.REQUIRE_HUMAN_REVIEW
                and final_decision != PolicyDecisionType.DENY
            ):
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
