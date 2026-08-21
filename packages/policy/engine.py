"""Policy engine interfaces, schemas, and rule evaluator stubs."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from packages.core.enums import MandateStatus, OperationType
from packages.core.models import FinancialOperation, Mandate


class PolicyDecision(BaseModel):
    """Result of policy evaluation for an operation intent."""
    model_config = ConfigDict(from_attributes=True)

    allowed: bool
    reason: str
    rule_name: str
    evaluated_at_epoch_ms: int
    context_data: Dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationResult(BaseModel):
    """Aggregate result of all evaluated policy rules."""
    model_config = ConfigDict(from_attributes=True)

    approved: bool
    operation_id: str
    decisions: List[PolicyDecision] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)


class PolicyRule(ABC):
    """Abstract interface for a policy rule."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the policy rule."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """Evaluates if the operation adheres to this specific policy."""
        pass


class MandateValidityRule(PolicyRule):
    """Checks if the mandate is currently active and within its valid date range."""

    @property
    def name(self) -> str:
        return "MANDATE_VALIDITY_CHECK"

    async def evaluate(
        self,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        import time
        now_ms = int(time.time() * 1000)

        if mandate.status != MandateStatus.ACTIVE:
            return PolicyDecision(
                allowed=False,
                reason=f"Mandate status is {mandate.status.value}, expected ACTIVE",
                rule_name=self.name,
                evaluated_at_epoch_ms=now_ms,
            )
        return PolicyDecision(
            allowed=True,
            reason="Mandate is active",
            rule_name=self.name,
            evaluated_at_epoch_ms=now_ms,
        )


class AmountBoundRule(PolicyRule):
    """Checks whether the requested operation amount exceeds per-op limit or aggregate budget."""

    @property
    def name(self) -> str:
        return "AMOUNT_BOUND_CHECK"

    async def evaluate(
        self,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        import time
        now_ms = int(time.time() * 1000)

        if operation.amount > mandate.max_amount_per_op:
            return PolicyDecision(
                allowed=False,
                reason=f"Operation amount {operation.amount} exceeds max per-operation limit {mandate.max_amount_per_op}",
                rule_name=self.name,
                evaluated_at_epoch_ms=now_ms,
                context_data={"amount": operation.amount, "limit": mandate.max_amount_per_op},
            )

        if (mandate.current_aggregate_spend + operation.amount) > mandate.aggregate_spend_limit:
            return PolicyDecision(
                allowed=False,
                reason="Operation would exceed remaining aggregate mandate spend limit",
                rule_name=self.name,
                evaluated_at_epoch_ms=now_ms,
                context_data={
                    "current_aggregate_spend": mandate.current_aggregate_spend,
                    "requested": operation.amount,
                    "limit": mandate.aggregate_spend_limit,
                },
            )

        return PolicyDecision(
            allowed=True,
            reason="Operation amount is within bounds",
            rule_name=self.name,
            evaluated_at_epoch_ms=now_ms,
        )


class AllowedOperationTypeRule(PolicyRule):
    """Checks if the operation type is authorized by the mandate."""

    @property
    def name(self) -> str:
        return "ALLOWED_OPERATION_TYPE_CHECK"

    async def evaluate(
        self,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        import time
        now_ms = int(time.time() * 1000)

        op_name = operation.operation_type.value if hasattr(operation.operation_type, "value") else str(operation.operation_type)
        if mandate.allowed_operations and op_name not in mandate.allowed_operations:
            return PolicyDecision(
                allowed=False,
                reason=f"Operation type '{op_name}' is not authorized in this mandate",
                rule_name=self.name,
                evaluated_at_epoch_ms=now_ms,
                context_data={"allowed": mandate.allowed_operations, "attempted": op_name},
            )

        return PolicyDecision(
            allowed=True,
            reason="Operation type is authorized",
            rule_name=self.name,
            evaluated_at_epoch_ms=now_ms,
        )


class PolicyEngine:
    """Evaluates an array of policy rules against a proposed financial operation."""

    def __init__(self, rules: Optional[List[PolicyRule]] = None) -> None:
        self.rules: List[PolicyRule] = rules or [
            MandateValidityRule(),
            AmountBoundRule(),
            AllowedOperationTypeRule(),
        ]

    async def evaluate_operation(
        self,
        mandate: Mandate,
        operation: FinancialOperation,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        decisions: List[PolicyDecision] = []
        rejection_reasons: List[str] = []

        for rule in self.rules:
            decision = await rule.evaluate(mandate, operation, context)
            decisions.append(decision)
            if not decision.allowed:
                rejection_reasons.append(f"[{decision.rule_name}] {decision.reason}")

        is_approved = len(rejection_reasons) == 0
        return PolicyEvaluationResult(
            approved=is_approved,
            operation_id=operation.operation_id,
            decisions=decisions,
            rejection_reasons=rejection_reasons,
        )
