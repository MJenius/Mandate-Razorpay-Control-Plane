# Mandate threat model

| Threat | Enforcement point | Automated verification | Invariant |
| --- | --- | --- | --- |
| Compromised agent or prompt injection | Deterministic policy engine and authenticated agent identity | `tests/test_policy.py`, `tests/test_security_and_failure_modes.py` | A denied operation never reaches the gateway. |
| Forged or replayed webhook | HMAC-SHA256 verification and unique event id | `tests/test_reliability_phase4.py` | A webhook cannot settle an operation twice. |
| Concurrent double spend | Conditional SQL budget reservation | `tests/test_evidence_claims.py` | committed + reserved spend never exceeds the mandate limit. |
| Delegation escalation or stale authority | Parent-chain and lifecycle policy rules | `tests/test_hierarchical_delegation_phase6.py` | An inactive ancestor invalidates delegated authority. |
| Rate-limit exhaustion | Per-agent Redis limiter; production fails closed if Redis is unavailable | `tests/test_rate_limiter.py` | One agent cannot consume another agent's quota. |
| Gateway timeout or worker crash | Reservation release and reconciliation worker | `tests/test_state_consistency.py` | Stale reservations are released or settled exactly once. |
