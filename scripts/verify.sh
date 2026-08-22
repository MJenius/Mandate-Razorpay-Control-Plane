#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "  [MANDATE VERIFICATION] >> Starting Full End-to-End System Verification"
echo "======================================================================"

echo "\n[1/4] Running Pytest Suite..."
python -m pytest -v --tb=short

echo "\n[2/4] Running MyPy Type Checks..."
python -m mypy apps packages services

echo "\n[3/4] Running 1,000 Scenario Empirical Benchmark..."
python -m packages.eval.large_scale_benchmark

echo "\n[4/4] Building Next.js Frontend Bundle..."
cd apps/web && npm run build && cd ../..

echo "\n======================================================================"
echo "  [SUCCESS] All Mandate Verification Steps Passed Cleanly!"
echo "======================================================================"
