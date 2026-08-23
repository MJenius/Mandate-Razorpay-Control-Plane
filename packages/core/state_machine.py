"""Formal Financial Operation State Machine with transition matrix and validation."""

from packages.core.enums import OperationStatus


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted on a FinancialOperation."""

    def __init__(
        self, current_status: OperationStatus, target_status: OperationStatus, reason: str = ""
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason
        super().__init__(
            f"Invalid state transition from '{current_status.value}' to '{target_status.value}'. {reason}".strip()
        )


class FinancialOperationStateMachine:
    """
    Formal Financial Operation State Machine Matrix:

    States:
      - INITIATED: Operation requested by agent, awaiting authentication and deterministic policy check
      - REQUIRES_APPROVAL: Policy requires human signoff before reservation
      - POLICY_APPROVED: Policy approved, ready for atomic budget reservation
      - POLICY_REJECTED: Policy denied operation (Zero-Gateway-Dispatch terminal)
      - RESERVED: Budget atomically reserved via CAS; ready for gateway dispatch
      - EXECUTING: Gateway request dispatched, awaiting synchronous response or asynchronous webhook
      - SUCCEEDED: Gateway confirmed order/payment; budget moved from reserved -> committed (terminal)
      - FAILED: Gateway rejected or execution aborted; reserved budget atomically released (terminal)
      - CANCELLED: Human approver or agent aborted operation before gateway execution (terminal)

    Transition Matrix:
      INITIATED -> [POLICY_APPROVED, POLICY_REJECTED, REQUIRES_APPROVAL, FAILED]
      REQUIRES_APPROVAL -> [RESERVED, POLICY_REJECTED, CANCELLED, FAILED]
      POLICY_APPROVED -> [RESERVED, FAILED, CANCELLED]
      RESERVED -> [EXECUTING, SUCCEEDED (out-of-order webhook), FAILED (gateway 5xx/timeout release), CANCELLED]
      EXECUTING -> [SUCCEEDED, FAILED, CANCELLED]
      CANCELLED -> []
      POLICY_REJECTED -> []
      RECONCILED -> []
    """

    ALLOWED_TRANSITIONS: dict[OperationStatus, set[OperationStatus]] = {
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
            OperationStatus.FAILED,     # Immediate reservation release on gateway failure
            OperationStatus.CANCELLED,
        },
        OperationStatus.EXECUTING: {
            OperationStatus.SUCCEEDED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        },
        # Terminal states have no valid outgoing transitions (re-affirmation is permitted idempotently)
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
    def validate_transition(
        cls, current: OperationStatus, target: OperationStatus, context_info: str = ""
    ) -> None:
        """Validates transition and raises InvalidStateTransitionError if illegal."""
        if not cls.can_transition(current, target):
            raise InvalidStateTransitionError(
                current_status=current,
                target_status=target,
                reason=f"Transition violates formal financial state machine invariants. {context_info}".strip(),
            )
