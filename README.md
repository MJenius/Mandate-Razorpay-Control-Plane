# Mandate

> **Financial authorization and control plane for AI agents operating through Razorpay APIs & MCP.**

[![CI/CD](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-44%20passed%20%7C%201%20skipped-success.svg)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)]()
[![Next.js](https://img.shields.io/badge/frontend-Next.js%2014-black.svg)]()

---

## What is Mandate?

**Mandate** is the deterministic financial safety boundary between autonomous AI agents and **Razorpay APIs**. While AI models are adept at understanding natural-language shopping and invoicing intents, giving an LLM direct API credentials or unrestricted Model Context Protocol (MCP) access allows hallucinations, prompt injections, and bug loops to drain merchant capital.

Mandate guarantees:
- **Zero-Gateway-Dispatch Invariant**: LLMs propose financial actions; Mandate's deterministic policy engine makes every authorization decision. Non-approved operations **never trigger Razorpay API calls**.
- **Two-Phase Budget Accounting**: Prevents budget drift by placing funds into `RESERVED` before gateway execution and committing only upon cryptographic webhook confirmation (`payment.captured`).
- **Hierarchical Single-Parent Delegation**: Parents can delegate bounded sub-mandates to child agents with mathematical non-escalation invariants. Revoking a parent mandate immediately cascades across all descendant children.
- **Razorpay Model Context Protocol (MCP) Security Gateway**: JSON-RPC 2.0 proxy that slashes exposed tool surfaces from 25+ tools down to 2–3 permitted schemas with strict parameter validation.

---

## System Architecture

```
User Intent / Prompt
        │
        ▼
AI Agent (Shopping / Procurement / Support)
        │
        ▼ (JSON-RPC 2.0 /tools/call)
Mandate MCP Security Gateway 
        │
        ├── 1. Dynamic Tool Surface Filtering (Slashes 25+ tools to 2-3)
        ├── 2. Strict Schema Validation (Rejects unauthorized injected args)
        ├── 3. Identity Resolution (Principal, Agent, Single-Parent Mandate)
        │
        ▼
Deterministic Policy Engine (8 Layered Rules)
   ├── AgentStatusRule
   ├── MandateLifecycleRule
   ├── HierarchicalDelegationRule (Tree Validation)
   ├── CurrencyMatchRule
   ├── AllowedOperationTypeRule
   ├── PerTransactionLimitRule
   ├── AggregateSpendLimitRule (CAS Budget Reservation)
   └── HumanReviewThresholdRule
        │
        ├─► [DENY] ──► Blocked (0 Razorpay API Calls Dispatched)
        │
        └─► [ALLOW] ──► Razorpay Client (Test Mode)
                              │
                              ▼
                         Razorpay Gateway API
                              │
                              ▼ (payment.captured webhook)
                         HMAC-SHA256 Webhook Pipeline
                              │
                              ▼
                         Atomic State Machine & Budget Commit
                              │
                              ▼
                         Immutable Audit Log & Delegation Trace
```

---

## Empirical Benchmark Results (`N = 1,000` Trials)

Evaluated across **800 hostile adversarial scenarios** (Overreaching, Compromised, Buggy, and Prompt-Injection agents) and **200 legitimate baseline operations** with seed `123`:

| Metric | Measured Value (`N=1,000`) | Guarantee |
| :--- | :---: | :--- |
| **Hostile Action Block Rate** | **100.0%** (800 / 800) | All unauthorized/corrupted financial requests intercepted. |
| **Policy Bypass Rate** | **0.0%** (0 / 800) | Zero unauthorized operations permitted. |
| **Unauthorized Razorpay Effects** | **0** | Strict Zero-Gateway-Dispatch invariant preserved. |
| **Legitimate Acceptance Rate** | **100.0%** (200 / 200) | Zero customer friction on valid operations. |
| **False Positive Rate (FPR)** | **0.0%** (0 / 200) | Compliant requests are never mistakenly blocked. |
| **Counterfactual Loss Prevented** | **₹21,85,00,000.00** | ₹21.85 Cr capital protected across 800 hostile vectors. |
| **Authorization Latency (P50)** | **6.31 ms** | Median policy decision overhead. |
| **Authorization Latency (P95)** | **12.22 ms** | P95 tail latency under high-load benchmarking. |

---

## Quickstart (Local & Docker Deployment)

### 1. Run with Docker Compose
```bash
# Start PostgreSQL, Redis, FastAPI Backend, Background Worker, and Next.js Frontend
docker compose up --build
```
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Competition Demo Mode**: [http://localhost:3000/demo](http://localhost:3000/demo)

### 2. Run Locally without Docker
```bash
# 1. Install dependencies
pip install -e ".[dev]"
cd apps/web && npm install && cd ../..

# 2. Run FastAPI Backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Run Background Reconciliation Worker
python -m services.worker.main

# 4. Run Frontend Dashboard
cd apps/web && npm run dev
```

---

## 5-Minute Competition Showcase

Navigate to [http://localhost:3000/demo](http://localhost:3000/demo) to execute the scripted 5-minute showcase:

1. **Clean-Slate Reset**: Seeds Alpha Commerce Enterprise, Shopping Master Agent, and Procurement Sub-Agent.
2. **Step 1 — Autonomous Buyer Commerce**: Purchases ₹6,500 Keychron keyboard within delegated ₹10,000 sub-mandate → `ALLOW`.
3. **Step 2 — Hostile Overreaching Attack**: Blocks 100x bulk order escalation (₹6.5L vs ₹10k limit) with `0 Razorpay API calls`.
4. **Step 3 — Compromised Cross-Role Attack**: Blocks unauthorized refund from shopping agent to external payment ID.
5. **Step 4 — Reliability Auto-Convergence**: Ingests Razorpay webhook with HMAC verification and transitions state from `RESERVED` → `SUCCEEDED`.
6. **Step 5 — Cascading Revocation**: Admin revokes root parent mandate, instantly invalidating all child authority across the delegation tree.

---

## Verification & Test Suite

Run the full hermetic test suite across all 8 phases:
```bash
python -m pytest tests/ -v
```
Run the 1,000-scenario reproducible benchmark:
```bash
python packages/eval/large_scale_benchmark.py
```
