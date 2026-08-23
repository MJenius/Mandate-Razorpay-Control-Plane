import pytest

from packages.core.enums import OperationStatus
from packages.core.state_machine import FinancialOperationStateMachine, InvalidStateTransitionError


def test_state_machine_rejects_every_unauthorized_terminal_mutation() -> None:
    for terminal in (OperationStatus.POLICY_REJECTED, OperationStatus.SUCCEEDED, OperationStatus.FAILED):
        for target in OperationStatus:
            if target != terminal:
                assert not FinancialOperationStateMachine.can_transition(terminal, target)
                with pytest.raises(InvalidStateTransitionError):
                    FinancialOperationStateMachine.validate_transition(terminal, target)
