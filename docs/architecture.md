# Architecture Design — Mandate Control Plane

## High-Level System Architecture

Mandate acts as an authorization boundary and execution control plane between **AI Autonomous Agents** and the **Razorpay Payment Gateway**.

```mermaid
flowchart TD
    subgraph AgenticPlane["AI Agent Intent Plane"]
        A1[Procurement Agent]
        A2[Support Refund Bot]
        A3[Subscription Bot]
    end

    subgraph ControlPlane["Mandate Authorization & Control Plane"]
        API[FastAPI Gateway / REST API]
        IDEMP[Idempotency Enforcer]
        POL[Policy Evaluation Engine]
        AUDIT[(Immutable Audit Trail)]
        DB[(PostgreSQL Domain Ledger)]
        CACHE[(Redis State / Lock)]
        WORKER[Async Worker Loop]
    end

    subgraph GatewayPlane["Razorpay Financial Gateway"]
        RZP_ORDER[Orders API]
        RZP_PAY[Payments API]
        RZP_REFUND[Refunds API]
        RZP_LINK[Payment Links API]
        RZP_HOOK[Webhook Ingestion]
    end

    A1 -->|Intent + Idempotency Key| API
    A2 -->|Intent + Idempotency Key| API
    A3 -->|Intent + Idempotency Key| API

    API --> IDEMP
    IDEMP --> CACHE
    API --> POL
    POL -->|Verify Mandate & Caps| DB
    POL -->|Audit Event| AUDIT
    AUDIT --> DB

    POL -->|Authorized Dispatch| WORKER
    WORKER --> RZP_ORDER
    WORKER --> RZP_PAY
    WORKER --> RZP_REFUND
    WORKER --> RZP_LINK

    RZP_HOOK --> API
```

---

## Core Architectural Invariants

1. **Strict Separation of Intent vs Authorization**:
   - An AI Agent **never** holds raw Razorpay API credentials.
   - An Agent submits financial intents to the Mandate Control Plane along with a unique `idempotency_key`.
   - The Policy Engine validates the intent against active, cryptographically signed Mandates before dispatching gateway calls.

2. **Bounded Financial Authority (Mandates)**:
   - Every operation is evaluated against per-operation limits and total aggregate spend limits.
   - Mandates have explicit validity time-windows and allowed operation sets.

3. **Deterministic Idempotency**:
   - Every financial operation requires an idempotency key. Duplicate submissions return cached operations without re-executing gateway transactions.

4. **Immutable Audit Trails**:
   - Every intent, policy evaluation, mandate change, and gateway event produces an append-only audit event in PostgreSQL.

5. **Typed Gateway Abstraction**:
   - The Razorpay client layer is fully typed and supports seamless switching between Test Mode mock execution and live Razorpay sandbox APIs.
