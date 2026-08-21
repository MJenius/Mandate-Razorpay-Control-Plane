# Mandate

> Financial authorization and control plane for AI agents operating through Razorpay APIs.

---

## Features (Phase 0 Foundation)

- **Monorepo Architecture**: Clean separation between API (`apps/api`), Frontend Dashboard (`apps/web`), Background Worker (`services/worker`), and domain packages (`packages/core`, `packages/policy`, `packages/razorpay`, `packages/events`, `packages/shared`).
- **Domain Foundation**: Rich domain models for Principals, AI Agents, Mandates, Financial Operations, Transactions, and Immutable Audit Events.
- **Typed Razorpay Abstraction**: Typed interfaces for Orders, Payments, Refunds, Payment Links, and HMAC Webhook verification with Test Mode support.
- **Policy Engine Gate**: Pre-flight policy checks enforcing budget bounds, per-op caps, and allowed operations before financial execution.
- **Idempotency & Auditing**: First-class idempotency key enforcement and append-only audit event logging.
- **Docker Compose Orchestration**: Single-command startup with PostgreSQL, Redis, FastAPI, Background Worker, and Next.js.
- **Continuous Integration**: GitHub Actions workflow for Ruff linting, MyPy static typing, Pytest test coverage, and Next.js frontend builds.

---

## Quickstart (Local Development)

### 1. Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run with Docker Compose (Recommended)
```bash
docker compose up --build
```
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Web Dashboard**: http://localhost:3000

---

## Running Locally Without Docker

### Backend (FastAPI + Worker)
```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Run Database & Redis (e.g. via docker compose up postgres redis -d)

# 3. Start API
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Start Background Worker (in separate terminal)
python -m services.worker.main
```

### Frontend (Next.js Dashboard)
```bash
cd apps/web
npm install
npm run dev
```

---

## Quality Checks & Testing

### Python Linter & Type Checker
```bash
ruff check .
ruff format --check .
mypy apps packages services
```

### Run Test Suite
```bash
pytest
```
