from packages.eval.chaos_harness import FailureMode, recovery_plan


def test_every_injected_failure_has_a_deterministic_recovery_path() -> None:
    assert {recovery_plan(mode).mechanism for mode in FailureMode} == {
        "release reservation", "reconciliation", "stale sweep", "production fail-closed", "conditional reservation"
    }
