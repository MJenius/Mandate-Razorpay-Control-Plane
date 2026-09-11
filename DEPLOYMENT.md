# Deployment Guide: Mandate Control Plane (Public Demo)

This guide details the step-by-step procedure to deploy **Mandate Control Plane** as a publicly accessible, interactive, reviewer-ready demo on **Render** and **Vercel**.

---

## 1. Architecture Overview

```mermaid
graph LR
    Browser["Reviewer Browser (/demo)"] -->|"HTTPS"| Vercel["Vercel (Next.js 14)"]
    Vercel -->|"NEXT_PUBLIC_API_URL"| RenderAPI["Render Web Service (FastAPI)"]
    RenderAPI -->|"SQLAlchemy AsyncEngine"| Postgres["Render PostgreSQL"]
    RenderAPI -->|"Redis / Key Value"| Redis["Render Key Value (Redis)"]
    Worker["Render Worker (Reconciliation)"] --> Postgres
    Worker --> Redis
```

| Component | Target Platform | Runtime / Base Image | Root Directory |
| :--- | :--- | :--- | :--- |
| **Frontend** | **Vercel** | Next.js 14 (Node 20) | `apps/web` |
| **Backend API** | **Render Web Service** | Python 3.12 / Uvicorn | Repository Root (`.`) |
| **Database** | **Render Managed PostgreSQL** | PostgreSQL 16 | N/A |
| **Cache / Rate Limiter** | **Render Key Value** | Redis 7+ Compatible | N/A |
| **Background Worker** | **Render Background Worker** | Python 3.12 | Repository Root (`.`) |

---

## 2. Prerequisites & Accounts

1. **GitHub Account**: Access to push changes to your repository: `https://github.com/MJenius/Mandate-Razorpay-Control-Plane`
2. **Render Account**: [https://render.com](https://render.com) (Free tier is sufficient)
3. **Vercel Account**: [https://vercel.com](https://vercel.com) (Hobby / Free tier is sufficient)

---

## 3. Backend Deployment on Render (Option A: 1-Click Blueprint — Recommended)

The repository includes a complete Infrastructure-as-Code specification in [`render.yaml`](file:///render.yaml).

### Steps:
1. Log in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository: `Mandate-Razorpay-Control-Plane`.
4. Render will parse `render.yaml` and display the stack components to be created:
   - **`mandate-api`** (Web Service)
   - **`mandate-worker`** (Background Worker)
   - **`mandate-postgres`** (PostgreSQL Database)
   - **`mandate-redis`** (Key Value instance)
5. Click **Apply**.
6. Render will automatically:
   - Provision PostgreSQL and Redis
   - Wire `DATABASE_URL` and `REDIS_URL` to both the Web Service and Worker
   - Generate secure random secrets for `SECRET_KEY`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`
   - Build and start the backend service
7. Once the `mandate-api` build finishes, copy your public Render URL:
   `https://mandate-api-xxxx.onrender.com`

---

## 4. Backend Deployment on Render (Option B: Manual Setup)

If you prefer to configure services manually without Blueprints:

### A. Create PostgreSQL Database
1. In Render Dashboard: **New +** → **PostgreSQL**.
2. Name: `mandate-postgres`.
3. Database Name: `mandate_db`, User: `mandate_user`.
4. Plan: **Free**.
5. Click **Create Database**.
6. Copy the **Internal Database URL** (e.g., `postgres://mandate_user:...@dpg-...-a/mandate_db`).

### B. Create Redis / Key Value
1. In Render Dashboard: **New +** → **Key Value**.
2. Name: `mandate-redis`.
3. Plan: **Free**.
4. Click **Create Key Value**.
5. Copy the **Internal Connection String** (e.g., `redis://...` or `rediss://...`).

### C. Create FastAPI Web Service
1. In Render Dashboard: **New +** → **Web Service**.
2. Connect repo: `Mandate-Razorpay-Control-Plane`.
3. Settings:
   - **Name**: `mandate-api`
   - **Language**: `Python`
   - **Root Directory**: Leave blank (repository root)
   - **Build Command**: `pip install --upgrade pip && pip install .`
   - **Start Command**: `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
4. Add Environment Variables (see Section 6).
5. Click **Create Web Service**.

### D. Create Background Worker
1. In Render Dashboard: **New +** → **Background Worker**.
2. Connect repo: `Mandate-Razorpay-Control-Plane`.
3. Settings:
   - **Name**: `mandate-worker`
   - **Language**: `Python`
   - **Build Command**: `pip install --upgrade pip && pip install .`
   - **Start Command**: `python -m services.worker.main`
4. Add the same database and redis environment variables as the Web Service.

---

## 5. Frontend Deployment on Vercel

1. Log in to [Vercel](https://vercel.com) and click **Add New...** → **Project**.
2. Import your GitHub repository: `Mandate-Razorpay-Control-Plane`.
3. In the **Configure Project** screen:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click **Edit** and select: `apps/web` (CRITICAL)
   - **Build Command**: `npm run build` (Default)
   - **Output Directory**: `.next` (Default)
   - **Install Command**: `npm install` (Default)
4. Under **Environment Variables**, add:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://<YOUR_RENDER_BACKEND_URL>` (e.g. `https://mandate-api.onrender.com` — do NOT include trailing slash)
5. Click **Deploy**.
6. Once deployed, note your public Vercel URL:
   `https://<YOUR_APP_NAME>.vercel.app`

### E. Update Backend CORS Origin
After Vercel assigns your public domain, update `ALLOWED_ORIGINS` in your Render Web Service:
- **`ALLOWED_ORIGINS`** = `https://<YOUR_APP_NAME>.vercel.app,http://localhost:3000`
- Click **Save Changes** (Render will automatically redeploy).

---

## 6. Environment Variables Reference Table

### A. Render Web Service (`mandate-api`)

| Variable | Recommended Value / Source | Secret? | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `demo` | No | Preserves security guardrails while enabling hermetic demo |
| `DEBUG` | `false` | No | Disables verbose debug logging |
| `LOG_LEVEL` | `INFO` | No | Application logging level |
| `AUTO_MIGRATE_ON_STARTUP` | `true` | No | Synchronizes PostgreSQL tables on clean database startup |
| `AUTO_SEED_DEMO` | `true` | No | Auto-seeds demo principals, 3 agents, and 3 mandates |
| `RAZORPAY_MOCK_MODE` | `true` | No | Strict mock mode: 0 live transactions moved |
| `RAZORPAY_KEY_ID` | `rzp_test_placeholder` | No | Test mode identifier |
| `RAZORPAY_KEY_SECRET` | Render generated or random 32 char | **Yes** | Test HMAC signing key |
| `RAZORPAY_WEBHOOK_SECRET` | Render generated or random 32 char | **Yes** | Webhook signature verification |
| `SECRET_KEY` | Render generated or random 32 char | **Yes** | Core encryption / token secret |
| `ALLOWED_ORIGINS` | `https://<YOUR_VERCEL_DOMAIN>` | No | Comma-separated list of permitted CORS web origins |
| `DATABASE_URL` | From `mandate-postgres` | **Yes** | Internal PostgreSQL connection string |
| `REDIS_URL` | From `mandate-redis` | **Yes** | Internal Key Value / Redis connection string |

### B. Render Background Worker (`mandate-worker`)

| Variable | Recommended Value | Secret? |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `demo` | No |
| `AUTO_MIGRATE_ON_STARTUP` | `false` | No |
| `RAZORPAY_MOCK_MODE` | `true` | No |
| `DATABASE_URL` | Same as `mandate-api` | **Yes** |
| `REDIS_URL` | Same as `mandate-api` | **Yes** |

### C. Vercel Frontend (`apps/web`)

| Variable | Recommended Value | Secret? | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://<RENDER_URL>` | No | Exposed to browser to dispatch requests to FastAPI backend |

> [!CAUTION]
> NEVER place database passwords, Razorpay secrets, or backend tokens into Vercel environment variables. Only `NEXT_PUBLIC_API_URL` belongs in the frontend!

---

## 7. Automated Live Deployment Verification

Once deployed, run the included verification script from your local terminal:

```bash
python scripts/verify_deployment.py \
  --backend https://<YOUR_RENDER_BACKEND>.onrender.com \
  --frontend https://<YOUR_VERCEL_FRONTEND>.vercel.app
```

The script will automatically check:
1. `/health` responds with `200 OK`
2. `/ready` reports PostgreSQL and Redis active
3. `/docs` Swagger specs are accessible
4. Frontend landing page `/` and `/demo` load cleanly
5. Live CORS preflight headers are permitted for the Vercel domain
6. Deterministic Policy Engine (8 rules) is verified
7. Executes Act 1 demonstration dry-run against the deployed backend

---

## 8. Manual Reviewer Experience Walkthrough

Open an Incognito browser window and navigate to:
`https://<YOUR_VERCEL_DOMAIN>/demo`

1. **Reviewer Landing**:
   - The top banner shows: `Control Plane: Active & Healthy`
   - The Razorpay badge displays: `Razorpay Sandbox: Test Mode`
2. **Execute Act 1: Compliant Agent Commerce Journey**:
   - Click **Execute Act 1** (or **Run Complete 5-Min Showcase**).
   - Observe real-time policy evaluation:
     - Policy Decision: `ALLOW`
     - Gateway Calls: `1` (Mock order created and captured)
     - Budget updated in real time.
3. **Execute Act 2: Adversarial Attack & Zero-Gateway-Dispatch**:
   - Click **Act 2**.
   - Reviewer observes:
     - Prompt injection attempting ₹6,50,000 order (100 units).
     - Policy Decision: `DENY`
     - Gateway Calls: Strictly `0` (Zero-Gateway-Dispatch Invariant verified).
4. **Execute Act 3: Webhook Failure & Self-Healing Reconciliation**:
   - Click **Act 3**.
   - Reviewer observes:
     - Simulated dropped webhook network partition.
     - Background reconciliation sweep detects discrepancy and auto-converges ledger state.
     - Policy Decision: `RECONCILED`.
5. **Reset Clean Slate**:
   - Click **Reset Clean Slate** anytime to re-seed deterministic enterprise state.

---

## 9. Submission URL Structure

For the submission form asking for *"Show us the magic. Paste a live link or working demo"*:

- **Primary Submission Link**: `https://<YOUR_VERCEL_DOMAIN>/demo`
- **Interactive API Documentation Link**: `https://<YOUR_RENDER_BACKEND>.onrender.com/docs`
- **Repository Link**: `https://github.com/MJenius/Mandate-Razorpay-Control-Plane`

---

## 10. Tear Down & Cost Management

Because this deployment uses free-tier services:
- **Render Free Tier**: Spin down Web Service and Worker when evaluation ends:
  - In Render Dashboard: Select service → **Settings** → **Suspend Service** (or **Delete Service**).
  - Delete PostgreSQL and Key Value instances.
- **Vercel Hobby Tier**: Zero idle costs; project can remain active indefinitely.
