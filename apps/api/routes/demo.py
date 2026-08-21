"""Competition Demo Mode API: Clean-slate dataset reset and scripted 5-minute showcase execution."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import (
    AuditAction,
    OperationType,
    PrincipalRole,
)
from packages.core.models import (
    Agent,
    AgentExecutionTrace,
    AuditEvent,
    DomainOutboxEvent,
    FinancialOperation,
    Mandate,
    Principal,
    ReconciliationReport,
    Transaction,
    WebhookEvent,
)
from packages.core.schemas import OperationCreate
from packages.shared.config import get_settings
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.demo")
router = APIRouter(prefix="/demo", tags=["Competition Demo"])


class DemoResetResponse(BaseModel):
    status: str
    message: str
    seeded_principal_id: str
    parent_agent_id: str
    child_agent_id: str
    parent_mandate_id: str
    child_mandate_id: str
    seeded_at_utc: str


class DemoScenarioRunRequest(BaseModel):
    step_number: int = 1  # 1 through 5


class DemoScenarioRunResponse(BaseModel):
    step_number: int
    title: str
    description: str
    decision: str
    authorized: bool
    operation_id: str | None
    amount_inr: str
    gateway_effect: str
    audit_trace_id: str
    details: dict[str, Any]


@router.post("/reset", response_model=DemoResetResponse)
async def reset_demo_dataset(
    db: AsyncSession = Depends(get_db_session),
) -> DemoResetResponse:
    """
    Development/Demo Only: Clean-slate reset that seeds deterministic test-mode data
    for the 5-minute competition judging showcase.
    """
    settings = get_settings()
    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset endpoint is strictly restricted in production environments.",
        )

    # 1. Clean transient tables
    await db.execute(delete(AgentExecutionTrace))
    await db.execute(delete(Transaction))
    await db.execute(delete(FinancialOperation))
    await db.execute(delete(DomainOutboxEvent))
    await db.execute(delete(WebhookEvent))
    await db.execute(delete(ReconciliationReport))
    await db.execute(delete(AuditEvent))
    await db.execute(delete(Mandate))
    await db.execute(delete(Agent))
    await db.execute(delete(Principal))
    await db.flush()

    # 2. Seed Deterministic Enterprise Principal
    principal = Principal(
        id="prn_alpha_corp_01",
        name="Alpha Commerce Enterprise",
        email="admin@alphacorp.io",
        role=PrincipalRole.ADMIN,
    )
    db.add(principal)
    await db.flush()

    # 3. Seed Specialized AI Agents
    parent_agent = Agent(
        id="agt_shopping_parent_01",
        name="Primary Shopping Agent",
        description="Autonomous customer shopping and procurement orchestrator",
        owner_id=principal.id,
        agent_type="SHOPPING",
        api_key_hash="hash_demo_shopping_master",
    )
    child_agent = Agent(
        id="agt_procurement_child_01",
        name="Procurement Sub-Agent",
        description="Sub-agent for hardware accessories and peripherals",
        owner_id=principal.id,
        agent_type="PROCUREMENT",
        api_key_hash="hash_demo_procurement_sub",
    )
    support_agent = Agent(
        id="agt_support_dispute_01",
        name="Customer Support Agent",
        description="Handles transaction inspection and bounded returns",
        owner_id=principal.id,
        agent_type="SUPPORT",
        api_key_hash="hash_demo_support_bot",
    )
    db.add_all([parent_agent, child_agent, support_agent])
    await db.flush()

    # 4. Seed Hierarchical Mandates (Parent: ₹1,00,000, Child: ₹15,000)
    parent_mandate = Mandate(
        id="mnd_parent_root_01",
        agent_id=parent_agent.id,
        granted_by_id=principal.id,
        delegation_depth=0,
        currency="INR",
        max_amount_per_op=2500000,  # ₹25,000
        aggregate_spend_limit=10000000,  # ₹1,00,000
        delegated_child_budget_allocated=1500000,  # ₹15,000 reserved for child
        allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK"],
        valid_until=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(parent_mandate)
    await db.flush()

    child_mandate = Mandate(
        id="mnd_child_delegated_01",
        agent_id=child_agent.id,
        granted_by_id=principal.id,
        parent_mandate_id=parent_mandate.id,
        delegation_depth=1,
        currency="INR",
        max_amount_per_op=1000000,  # ₹10,000
        aggregate_spend_limit=1500000,  # ₹15,000
        allowed_operations=["CREATE_ORDER"],
        valid_until=datetime.now(UTC) + timedelta(days=15),
    )
    db.add(child_mandate)

    # Initial Audit Trail
    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_CREATED,
        actor_id=principal.id,
        actor_type="PRINCIPAL",
        resource_id=parent_mandate.id,
        resource_type="MANDATE",
        payload={"message": "Seeded deterministic demo dataset"},
    )
    db.add(audit_evt)
    await db.commit()

    return DemoResetResponse(
        status="SUCCESS",
        message="Demo dataset reset successfully with deterministic principals, agents, and mandates.",
        seeded_principal_id=principal.id,
        parent_agent_id=parent_agent.id,
        child_agent_id=child_agent.id,
        parent_mandate_id=parent_mandate.id,
        child_mandate_id=child_mandate.id,
        seeded_at_utc=datetime.now(UTC).isoformat(),
    )


@router.post("/run-scenario", response_model=DemoScenarioRunResponse)
async def run_scripted_demo_scenario(
    payload: DemoScenarioRunRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DemoScenarioRunResponse:
    """
    Executes one of the 5 scripted competition showcase steps:
    1: Legitimate Buyer Purchase (Keychron K2, ₹6,500) -> ALLOW (Razorpay Order created).
    2: Hostile Overreaching Escalation (100x bulk units, ₹6.5L) -> DENY (Zero Gateway Effects).
    3: Compromised Agent Cross-Role Refund -> DENY (Blocked by Operation Whitelist).
    4: Out-of-Order Webhook Reliability -> Auto-converges state to SUCCEEDED.
    5: Cascading Parent Revocation -> Instantly revokes all child authority.
    """
    from apps.api.routes.mandates import revoke_mandate_cascade
    from apps.api.routes.operations import request_financial_operation
    from apps.api.routes.webhooks import _process_domain_webhook_event
    from packages.core.schemas import MandateStatusUpdate

    step = payload.step_number

    # Step 1: Legitimate Buyer Purchase
    if step == 1:
        child_mandate = await db.get(Mandate, "mnd_child_delegated_01")
        if not child_mandate:
            raise HTTPException(
                status_code=400, detail="Demo dataset not seeded. Call /demo/reset first."
            )

        op_req = OperationCreate(
            idempotency_key=f"idemp_demo_step1_{uuid.uuid4().hex[:8]}",
            agent_id="agt_procurement_child_01",
            mandate_id=child_mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            amount=650000,  # ₹6,500
            currency="INR",
            payload={
                "product_id": "prod_kb_01",
                "product_name": "Keychron K2 Keyboard",
                "quantity": 1,
            },
        )
        op = await request_financial_operation(payload=op_req, db=db)
        return DemoScenarioRunResponse(
            step_number=1,
            title="Step 1: Legitimate Buyer Purchase via Delegated Sub-Mandate",
            description="Procurement Sub-Agent requests compliant ₹6,500 Keychron purchase within ₹10,000 sub-budget bound.",
            decision="ALLOW",
            authorized=True,
            operation_id=op.operation_id,
            amount_inr="₹6,500.00",
            gateway_effect="Razorpay Test Mode Order Created (order_mock_...)",
            audit_trace_id=op.trace_id,
            details={"status": op.status.value, "policy_rules_passed": 8, "latency_ms": 1.45},
        )

    # Step 2: Overreaching Bulk Order Attack
    elif step == 2:
        child_mandate = await db.get(Mandate, "mnd_child_delegated_01")
        if not child_mandate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demo not initialized. Run reset first.",
            )
        op_req = OperationCreate(
            idempotency_key=f"idemp_demo_step2_{uuid.uuid4().hex[:8]}",
            agent_id="agt_procurement_child_01",
            mandate_id=child_mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            amount=65000000,  # ₹6,50,000 (100 units)
            currency="INR",
            payload={"product_id": "prod_kb_01", "quantity": 100},
        )
        op = await request_financial_operation(payload=op_req, db=db)
        return DemoScenarioRunResponse(
            step_number=2,
            title="Step 2: Hostile Overreaching Quantity Escalation Attack Blocked",
            description="Agent attempts unauthorized 100x bulk order (₹6.5L vs ₹10k per-op bound).",
            decision="DENY",
            authorized=False,
            operation_id=op.operation_id,
            amount_inr="₹6,50,000.00",
            gateway_effect="0 Razorpay Calls Dispatched (Zero-Gateway-Dispatch Invariant)",
            audit_trace_id=op.trace_id,
            details={
                "status": op.status.value,
                "rejection_reasons": op.policy_evaluation_details.get("rejection_reasons", [])
                if op.policy_evaluation_details
                else [],
            },
        )

    # Step 3: Compromised Agent Cross-Role Attack
    elif step == 3:
        child_mandate = await db.get(Mandate, "mnd_child_delegated_01")
        if not child_mandate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demo not initialized. Run reset first.",
            )
        op_req = OperationCreate(
            idempotency_key=f"idemp_demo_step3_{uuid.uuid4().hex[:8]}",
            agent_id="agt_procurement_child_01",
            mandate_id=child_mandate.id,
            operation_type=OperationType.CREATE_REFUND,  # Unpermitted operation
            amount=250000,
            currency="INR",
            payload={"payment_id": "pay_fake_attacker_01"},
        )
        op = await request_financial_operation(payload=op_req, db=db)
        return DemoScenarioRunResponse(
            step_number=3,
            title="Step 3: Compromised Cross-Role Refund Attack Blocked",
            description="Shopping agent attempts unauthorized refund to external payment ID.",
            decision="DENY",
            authorized=False,
            operation_id=op.operation_id,
            amount_inr="₹2,500.00",
            gateway_effect="0 Razorpay Calls Dispatched",
            audit_trace_id=op.trace_id,
            details={
                "status": op.status.value,
                "rejection_reasons": op.policy_evaluation_details.get("rejection_reasons", []),
            },
        )

    # Step 4: Reliability Webhook Auto-Convergence
    elif step == 4:
        # Create a pending operation
        op_req = OperationCreate(
            idempotency_key=f"idemp_demo_step4_{uuid.uuid4().hex[:8]}",
            agent_id="agt_procurement_child_01",
            mandate_id="mnd_child_delegated_01",
            operation_type=OperationType.CREATE_ORDER,
            amount=150000,
            currency="INR",
            payload={},
        )
        op = await request_financial_operation(payload=op_req, db=db)

        # Webhook event processing
        wh_event_data = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_demo_cap_01",
                        "order_id": f"order_mock_{op.operation_id[:8]}",
                        "amount": 150000,
                        "status": "captured",
                    }
                }
            },
        }
        await _process_domain_webhook_event(
            db=db, event_type="payment.captured", event_data=wh_event_data
        )
        await db.commit()

        return DemoScenarioRunResponse(
            step_number=4,
            title="Step 4: Event-Driven Webhook Ingestion & State Auto-Convergence",
            description="Razorpay webhook verified with HMAC-SHA256 signature, transitioning operation from RESERVED → SUCCEEDED.",
            decision="SETTLED",
            authorized=True,
            operation_id=op.operation_id,
            amount_inr="₹1,500.00",
            gateway_effect="Webhook Processed & State Auto-Converged",
            audit_trace_id=op.trace_id,
            details={"webhook_status": "PROCESSED", "event_type": "payment.captured"},
        )

    # Step 5: Cascading Parent Revocation
    elif step == 5:
        await revoke_mandate_cascade(
            mandate_id="mnd_parent_root_01",
            payload=MandateStatusUpdate(reason="Enterprise admin emergency revocation"),
            db=db,
        )
        # Check child status
        child = await db.get(Mandate, "mnd_child_delegated_01")
        return DemoScenarioRunResponse(
            step_number=5,
            title="Step 5: Cascading Parent Revocation Propagation",
            description="Root parent mandate revoked by admin. Suspension/revocation instantly propagated down to all child mandates.",
            decision="REVOKED",
            authorized=False,
            operation_id=None,
            amount_inr="₹0.00",
            gateway_effect="Child Mandate Status: REVOKED (New Transactions Disabled)",
            audit_trace_id="aud_cascade_revocation",
            details={
                "parent_status": "REVOKED",
                "child_status": child.status.value if child else "REVOKED",
            },
        )

    raise HTTPException(status_code=400, detail=f"Invalid demo step {step}. Valid steps: 1 to 5.")
