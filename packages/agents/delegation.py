"""Multi-Agent Collaborative Commerce Workflows linking User -> Shopping -> Procurement -> Risk -> Mandate -> Razorpay."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.agents.runner import AgentRunner
from packages.core.enums import OperationType
from packages.core.models import Agent, FinancialOperation, Mandate, Transaction
from packages.core.schemas import OperationCreate
from packages.shared.logging import get_logger

logger = get_logger("agents.delegation")


class CollaborativeCommerceResult:
    def __init__(
        self,
        order_id: Optional[str],
        operation_id: Optional[str],
        policy_decision: str,
        risk_score: float,
        shopping_agent_id: str,
        procurement_agent_id: str,
        total_amount_paise: int,
        details: Dict[str, Any],
    ) -> None:
        self.order_id = order_id
        self.operation_id = operation_id
        self.policy_decision = policy_decision
        self.risk_score = risk_score
        self.shopping_agent_id = shopping_agent_id
        self.procurement_agent_id = procurement_agent_id
        self.total_amount_paise = total_amount_paise
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "operation_id": self.operation_id,
            "policy_decision": self.policy_decision,
            "risk_score": self.risk_score,
            "shopping_agent_id": self.shopping_agent_id,
            "procurement_agent_id": self.procurement_agent_id,
            "total_amount_inr": f"Rs. {self.total_amount_paise / 100:,.2f}",
            "details": self.details,
        }


class CollaborativeCommerceCoordinator:
    """
    Coordinates multi-agent commerce execution:
    User Prompt -> Shopping Agent (interprets customer intent) ->
    Delegates scoped sub-order to Procurement Agent ->
    Risk Agent assesses velocity and anomaly score ->
    Mandate Policy Engine validates hierarchical tree bounds ->
    Razorpay Test Mode executes -> Immutable Audit Chain recorded.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute_procurement_flow(
        self,
        shopping_agent: Agent,
        procurement_agent: Agent,
        child_mandate: Mandate,
        product_id: str,
        quantity: int,
        customer_name: str,
    ) -> CollaborativeCommerceResult:
        from apps.api.routes.operations import request_financial_operation
        from packages.agents.tools import PRODUCTS_CATALOG

        product = PRODUCTS_CATALOG.get(product_id)
        if not product:
            raise ValueError(f"Product '{product_id}' not found in catalog")

        total_amount = product["price_paise"] * quantity

        # 1. Simulated Risk Agent Scoring (Anomaly check)
        risk_score = 0.05 if total_amount <= child_mandate.max_amount_per_op else 0.85
        risk_passed = risk_score < 0.50

        # 2. Intercept through Mandate Policy Gate
        op_req = OperationCreate(
            idempotency_key=f"idemp_collab_{uuid.uuid4().hex}",
            agent_id=procurement_agent.id,
            mandate_id=child_mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            amount=total_amount,
            currency="INR",
            payload={
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "customer_name": customer_name,
                "delegated_by_agent_id": shopping_agent.id,
                "risk_agent_score": risk_score,
            },
        )

        op = await request_financial_operation(payload=op_req, db=self.db)
        decision = op.policy_evaluation_details.get("decision", "DENY")

        # Explicit async query for transaction to prevent lazy-loading greenlet errors
        tx_stmt = select(Transaction).where(Transaction.operation_id == op.id)
        tx_res = await self.db.execute(tx_stmt)
        tx = tx_res.scalar_one_or_none()
        order_id = tx.gateway_order_id if tx else None

        return CollaborativeCommerceResult(
            order_id=order_id,
            operation_id=op.operation_id,
            policy_decision=decision,
            risk_score=risk_score,
            shopping_agent_id=shopping_agent.id,
            procurement_agent_id=procurement_agent.id,
            total_amount_paise=total_amount,
            details={
                "product": product["name"],
                "quantity": quantity,
                "customer": customer_name,
                "status": op.status.value,
                "error_message": op.error_message,
            },
        )
