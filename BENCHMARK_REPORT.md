# Mandate local validation report

All results in this document were generated locally using Docker Compose, PostgreSQL, Redis, FastAPI, and Razorpay mock mode. No paid cloud infrastructure or production Razorpay transaction was used.

## A. Adversarial authorization evaluation

`packages/eval/large_scale_benchmark.py` and `tests/test_evidence_claims.py` exercise 1,430 deterministic scenarios: 1,144 hostile and 286 legitimate. The checked invariant is that a denied operation has zero gateway dispatches. These are simulated authorization inputs, not production traffic.

```bash
python -m packages.eval.large_scale_benchmark
python -m pytest tests/test_evidence_claims.py -v
```

## B. Authorization correctness

The policy engine, hierarchical delegation checks, webhook verification, and idempotency behavior are verified in the local pytest suite. The suite uses a deterministic Razorpay mock; it does not measure a live payment provider.

## C. PostgreSQL concurrency evaluation

Command run on 2026-08-23 against the Docker Compose PostgreSQL 16 container:

```bash
python scripts/benchmark_concurrency.py --concurrency 100,200,500 --trials 2
```

Each attempt opens a real PostgreSQL transaction, creates an operation row, and calls the same conditional `UPDATE` reservation primitive used by the API. The benchmark queries mandate and operation rows independently after every trial before cleaning up its isolated data. `Committed + Reserved <= Limit` passed in all 12 trials; the table shows the mean latency across the two trials.

| Scenario | Concurrency | P50 ms | P95 ms | P99 ms | Rejected / CAS conflicts | Overspend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Independent mandates | 100 | 960.1 | 1116.1 | 1124.4 | 0 | 0 |
| Independent mandates | 200 | 1140.8 | 1479.2 | 1506.6 | 0 | 0 |
| Independent mandates | 500 | 1859.1 | 2668.7 | 2713.3 | 0 | 0 |
| Shared mandate | 100 | 976.4 | 1175.8 | 1219.4 | 50 | 0 |
| Shared mandate | 200 | 1336.8 | 1669.8 | 1755.8 | 100 | 0 |
| Shared mandate | 500 | 2291.9 | 3301.8 | 3362.8 | 250 | 0 |

The high-contention mandate permits exactly half of requests. Every trial recorded the expected successful reservations, zero failed database operations, zero ledger entries (no gateway dispatch is part of this reservation benchmark), and:

**PASS — ZERO OVERSPEND**

Generated JSON and CSV are written to `benchmarks/results/` and intentionally ignored by Git. Rerun the command to reproduce them on a local machine.

## D. Failure and recovery evaluation

Local integration tests cover gateway failures, dropped and replayed webhooks, duplicate operations, stale reservations, out-of-order webhooks, and reconciliation. The result asserted is converged financial state: a reservation is either committed once or released once.

```bash
python -m pytest tests/test_reliability_phase4.py tests/test_security_and_failure_modes.py tests/test_state_consistency.py tests/test_chaos_and_recovery.py -v
```

## Reproduction commands

```bash
docker compose up -d postgres redis
python -m pytest -q
python scripts/benchmark_concurrency.py --concurrency 100,200,500 --trials 3
python loadtests/run_contention_analysis.py --concurrency 100,200,500
```

Limitations: latency figures are local-machine measurements, not capacity claims. The reservation benchmark does not invoke Razorpay or create settlement ledger entries; payment settlement is covered separately by the webhook and reconciliation tests.
