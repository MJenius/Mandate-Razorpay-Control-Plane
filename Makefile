.PHONY: help verify test mypy benchmark build-web dev

help:
	@echo "Mandate - Autonomous Financial Authorization Control Plane"
	@echo "Available commands:"
	@echo "  make verify      - Run full verification (tests, mypy, benchmark, frontend build)"
	@echo "  make test        - Run backend pytest test suite"
	@echo "  make mypy        - Run static type checker"
	@echo "  make benchmark   - Run N=1,000 scenarios empirical evaluation"
	@echo "  make build-web   - Build Next.js production bundle"

verify:
	python scripts/verify.py

test:
	python -m pytest -v

mypy:
	python -m mypy apps packages services

benchmark:
	python -m packages.eval.large_scale_benchmark

build-web:
	cd apps/web && npm run build
