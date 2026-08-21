"""Formal Financial Operation State Machine with transition matrix and validation."""

from typing import Dict, Set
from packages.core.enums import OperationStatus


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted on a FinancialOperation."""

    def __init__(self, current_status: OperationStatus, target_status: OperationStatus, reason: str = "") -> None:
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason
        super().__init__(
            f"Invalid state transition from '{current_status.value}' to '{target_status.value}'. {reason}".strip()
        )


class FinancialOperationStateMachine:
    """
    Strict State Transition Matrix for Financial Operations:

    INITIATED -> [POLICY_APPROVED, POLICY_REJECTED, REQUIRES_APPROVAL, FAILED]
    REQUIRES_APPROVAL -> [RESERVED, POLICY_REJECTED, CANCELLED, FAILED]
    POLICY_APPROVED -> [RESERVED, FAILED, CANCELLED]
    RESERVED -> [EXECUTING, FAILED, CANCELLED]
    EXECUTING -> [SUCCEEDED, FAILED, CANCELLED]
    SUCCEEDED -> [] (Terminal State)
    FAILED -> [] (Terminal State)
    CANCELLED -> [] (Terminal State)
    POLICY_REJECTED -> [] (Terminal State)
    """

    ALLOWED_TRANSITIONS: Dict[OperationStatus, Set[OperationStatus]] = {
        OperationStatus.INITIATED: {
            OperationStatus.POLICY_APPROVED,
            OperationStatus.POLICY_REJECTED,
            OperationStatus.REQUIRES_APPROVAL,
            OperationStatus.FAILED,
        },
        OperationStatus.REQUIRES_APPROVAL: {
            OperationStatus.RESERVED,
            OperationStatus.POLICY_REJECTED,
            OperationStatus.CANCELLED,
            OperationStatus.FAILED,
        },
        OperationStatus.POLICY_APPROVED: {
            OperationStatus.RESERVED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        },
        OperationStatus.RESERVED: {
            OperationStatus.EXECUTING,
            OperationStatus.SUCCEEDED,  # Direct convergence via out-of-order webhook
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        },
        OperationStatus.EXECUTING: {
            OperationStatus.SUCCEEDED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        },
        # Terminal states have no valid outgoing transitions
        OperationStatus.SUCCEEDED: set(),
        OperationStatus.FAILED: set(),
        OperationStatus.CANCELLED: set(),
        OperationStatus.POLICY_REJECTED: set(),
    }

    @classmethod
    def can_transition(cls, current: OperationStatus, target: OperationStatus) -> bool:
        """Returns True if transition from current to target is allowed."""
        if current == target:
            return True  # Idempotent re-affirmation is permitted
        return target in cls.ALLOWED_TRANSITIONS.get(current, set())

    @classmethod
    def validate_transition(cls, current: OperationStatus, target: OperationStatus, context_info: str = "") -> None:
        """Validates transition and raises InvalidStateTransitionError if illegal."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(
                current_status=current,
                target_status=target,
                reason=f"Transition violates formal financial state machine invariants. {context_info}".strip(),
            )
