from hypothesis import given
from hypothesis import strategies as st

from packages.core.enums import OperationStatus
from packages.core.state_machine import FinancialOperationStateMachine


@given(st.sampled_from(list(OperationStatus)), st.sampled_from(list(OperationStatus)))
def test_terminal_states_never_authorize_a_new_operation(current: OperationStatus, target: OperationStatus) -> None:
    if current in {OperationStatus.POLICY_REJECTED, OperationStatus.SUCCEEDED, OperationStatus.FAILED, OperationStatus.CANCELLED}:
        assert FinancialOperationStateMachine.can_transition(current, target) == (current == target)
