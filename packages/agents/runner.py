"""Agent Tool-Calling Execution Runtime connecting LLM proposed actions to Mandate Policy Gate."""

import json
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.agents.adapter import BaseLLMAdapter, LLMToolCall, get_llm_adapter
from packages.agents.prompts import SHOPPING_AGENT_SYSTEM_PROMPT, SUPPORT_AGENT_SYSTEM_PROMPT
from packages.agents.tools import (
    PRODUCTS_CATALOG,
    SHOPPING_AGENT_TOOLS,
    SUPPORT_AGENT_TOOLS,
    execute_local_catalog_tool,
)
from packages.core.enums import OperationType
from packages.core.models import Agent, AgentExecutionTrace, Mandate
from packages.core.schemas import OperationCreate
from packages.shared.logging import get_logger

logger = get_logger("agents.runner")


class AgentRunnerResult:
    def __init__(
        self,
        reply: str,
        session_id: str,
        tool_calls: List[Dict[str, Any]],
        policy_decisions: List[Dict[str, Any]],
        operation_ids: List[str],
        latency_ms: float,
    ) -> None:
        self.reply = reply
        self.session_id = session_id
        self.tool_calls = tool_calls
        self.policy_decisions = policy_decisions
        self.operation_ids = operation_ids
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply": self.reply,
            "session_id": self.session_id,
            "tool_calls": self.tool_calls,
            "policy_decisions": self.policy_decisions,
            "operation_ids": self.operation_ids,
            "latency_ms": self.latency_ms,
        }


class AgentRunner:
    """Orchestrates agent conversations, invokes LLMAdapter, and converts tool calls to Mandate operations."""

    def __init__(self, db: AsyncSession, adapter: Optional[BaseLLMAdapter] = None) -> None:
        self.db = db
        self.adapter = adapter or get_llm_adapter()

    async def execute_turn(
        self,
        agent: Agent,
        mandate: Mandate,
        user_prompt: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentRunnerResult:
        start_time = time.perf_counter()
        active_session = session_id or f"sess_{uuid.uuid4().hex[:12]}"

        # Select tools & system prompt by agent type
        if agent.agent_type.upper() == "SUPPORT":
            system_prompt = SUPPORT_AGENT_SYSTEM_PROMPT
            tools = SUPPORT_AGENT_TOOLS
        else:
            system_prompt = SHOPPING_AGENT_SYSTEM_PROMPT
            tools = SHOPPING_AGENT_TOOLS

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_prompt})

        # 1. First LLM Turn: Request tool choice
        llm_resp = await self.adapter.chat_completion(messages=messages, tools=tools)

        executed_tool_calls: List[Dict[str, Any]] = []
        policy_decisions: List[Dict[str, Any]] = []
        operation_ids: List[str] = []

        # 2. If Model invoked tools, execute them against Mandate
        if llm_resp.tool_calls:
            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": llm_resp.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in llm_resp.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in llm_resp.tool_calls:
                tool_result, op_id, decision_data = await self._dispatch_agent_tool(
                    agent=agent,
                    mandate=mandate,
                    tool_name=tc.name,
                    args=tc.arguments,
                )

                executed_tool_calls.append({"name": tc.name, "arguments": tc.arguments, "result": tool_result})
                if op_id:
                    operation_ids.append(op_id)
                if decision_data:
                    policy_decisions.append(decision_data)

                # Feed tool result back to LLM context
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": json.dumps(tool_result),
                })

                # Persist Execution Trace (Separate from reasoning)
                trace = AgentExecutionTrace(
                    session_id=active_session,
                    agent_id=agent.id,
                    user_prompt=user_prompt,
                    model_provider=llm_resp.provider,
                    model_name=llm_resp.model,
                    tool_name=tc.name,
                    tool_arguments=tc.arguments,
                    tool_result=tool_result,
                    operation_id=op_id,
                    policy_decision=decision_data.get("decision") if decision_data else None,
                    agent_response_text="",
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                )
                self.db.add(trace)

            # 3. Second LLM Turn: Allow agent to formulate natural language response with tool result
            final_resp = await self.adapter.chat_completion(messages=messages)
            reply_text = final_resp.content or "Action processed successfully."
        else:
            reply_text = llm_resp.content or "I am here to assist you."

        total_latency = round((time.perf_counter() - start_time) * 1000, 2)
        await self.db.commit()

        return AgentRunnerResult(
            reply=reply_text,
            session_id=active_session,
            tool_calls=executed_tool_calls,
            policy_decisions=policy_decisions,
            operation_ids=operation_ids,
            latency_ms=total_latency,
        )

    async def _dispatch_agent_tool(
        self,
        agent: Agent,
        mandate: Mandate,
        tool_name: str,
        args: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[str], Optional[Dict[str, Any]]]:
        """Routes agent tool call to Mandate's operations pipeline."""
        from apps.api.routes.operations import request_financial_operation

        # Local informational tools (non-financial)
        if tool_name == "browse_catalog":
            return execute_local_catalog_tool(tool_name, args), None, None

        if tool_name == "lookup_transaction":
            from packages.core.models import FinancialOperation
            op_id = args.get("operation_id", "")
            stmt = select(FinancialOperation).where(FinancialOperation.operation_id == op_id)
            res = await self.db.execute(stmt)
            op = res.scalar_one_or_none()
            if not op:
                return {"error": f"Operation '{op_id}' not found"}, None, None
            return {
                "operation_id": op.operation_id,
                "status": op.status.value,
                "amount_inr": f"Rs. {op.amount / 100:,.2f}",
                "operation_type": op.operation_type.value,
                "created_at": op.created_at.isoformat(),
            }, op.operation_id, None

        # Financial Operations -> Routed strictly through Mandate Policy Gate
        if tool_name == "create_purchase_order":
            product_id = args.get("product_id")
            quantity = max(1, int(args.get("quantity", 1)))
            product = PRODUCTS_CATALOG.get(product_id)

            if not product:
                return {"error": f"Product '{product_id}' does not exist in catalog"}, None, None

            total_amount_paise = product["price_paise"] * quantity

            op_req = OperationCreate(
                idempotency_key=f"idemp_ag_{uuid.uuid4().hex}",
                agent_id=agent.id,
                mandate_id=mandate.id,
                operation_type=OperationType.CREATE_ORDER,
                amount=total_amount_paise,
                currency="INR",
                payload={
                    "product_id": product_id,
                    "product_name": product["name"],
                    "quantity": quantity,
                    "customer_name": args.get("customer_name", "Valued Customer"),
                },
            )
            op = await request_financial_operation(payload=op_req, db=self.db)
            decision = op.policy_evaluation_details.get("decision", "DENY")

            return {
                "operation_id": op.operation_id,
                "status": op.status.value,
                "policy_decision": decision,
                "amount_inr": f"Rs. {op.amount / 100:,.2f}",
                "error_message": op.error_message,
                "product": product["name"],
            }, op.operation_id, op.policy_evaluation_details

        if tool_name == "create_payment_link_for_customer":
            amount_inr = float(args.get("amount_in_rupees", 0))
            amount_paise = int(amount_inr * 100)

            op_req = OperationCreate(
                idempotency_key=f"idemp_plink_{uuid.uuid4().hex}",
                agent_id=agent.id,
                mandate_id=mandate.id,
                operation_type=OperationType.CREATE_PAYMENT_LINK,
                amount=amount_paise,
                currency="INR",
                payload={
                    "description": args.get("description", "Mandate Invoice"),
                    "customer_name": args.get("customer_name"),
                    "customer_email": args.get("customer_email"),
                },
            )
            op = await request_financial_operation(payload=op_req, db=self.db)
            decision = op.policy_evaluation_details.get("decision", "DENY")

            return {
                "operation_id": op.operation_id,
                "status": op.status.value,
                "policy_decision": decision,
                "amount_inr": f"Rs. {op.amount / 100:,.2f}",
                "error_message": op.error_message,
            }, op.operation_id, op.policy_evaluation_details

        if tool_name == "issue_customer_refund":
            payment_id = args.get("payment_id", "")
            amount_inr = args.get("amount_in_rupees")
            amount_paise = int(float(amount_inr) * 100) if amount_inr else 50000

            op_req = OperationCreate(
                idempotency_key=f"idemp_rfnd_{uuid.uuid4().hex}",
                agent_id=agent.id,
                mandate_id=mandate.id,
                operation_type=OperationType.CREATE_REFUND,
                amount=amount_paise,
                currency="INR",
                payload={"payment_id": payment_id, "reason": args.get("reason", "Customer requested refund")},
            )
            op = await request_financial_operation(payload=op_req, db=self.db)
            decision = op.policy_evaluation_details.get("decision", "DENY")

            return {
                "operation_id": op.operation_id,
                "status": op.status.value,
                "policy_decision": decision,
                "amount_inr": f"Rs. {op.amount / 100:,.2f}",
                "payment_id": payment_id,
                "error_message": op.error_message,
            }, op.operation_id, op.policy_evaluation_details

        return {"error": f"Unauthorized tool invocation '{tool_name}'"}, None, None
