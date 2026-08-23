.PHONY: help verify test mypy benchmark chaos build-web dev

help:
	@echo "Mandate - Autonomous Financial Authorization Control Plane"
	@echo "Available commands:"
	@echo "  make verify      - Run full verification (tests, mypy, benchmark, frontend build)"
	@echo "  make test        - Run backend pytest test suite"
	@echo "  make mypy        - Run static type checker"
	@echo "  make benchmark   - Run PostgreSQL concurrency benchmark (Docker required)"
	@echo "  make chaos       - Run failure-recovery and property checks"
	@echo "  make build-web   - Build Next.js production bundle"

verify:
	python scripts/verify.py

test:
	python -m pytest -v

mypy:
	python -m mypy apps packages services

benchmark:
	python scripts/benchmark_concurrency.py --concurrency 100,200,500 --trials 3

chaos:
	python -m pytest tests/test_reliability_phase4.py tests/test_security_and_failure_modes.py tests/test_state_consistency.py tests/test_chaos_and_recovery.py tests/test_properties_hypothesis.py -v

build-web:
	cd apps/web && npm run build
