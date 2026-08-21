"""Multi-provider LLM Adapter supporting OpenAI, mock hermetic runner, and future providers."""

import json
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field

from packages.shared.config import get_settings
from packages.shared.logging import get_logger

logger = get_logger("agents.adapter")


class LLMToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    model: str
    provider: str


class BaseLLMAdapter(ABC):
    """Abstract base adapter for LLM tool-calling backends."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        pass


class OpenAILLMAdapter(BaseLLMAdapter):
    """OpenAI API implementation for structured tool calling."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured in environment")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as err:
                if err.response.status_code == 429:
                    logger.warning("openai_rate_limit_exceeded_falling_back_to_semantic_mock")
                    mock_adapter = MockLLMAdapter()
                    return await mock_adapter.chat_completion(messages=messages, tools=tools)
                raise
            except Exception as ex:
                logger.warning("openai_api_error_falling_back", error=str(ex))
                mock_adapter = MockLLMAdapter()
                return await mock_adapter.chat_completion(messages=messages, tools=tools)

        choice = data["choices"][0]["message"]
        content = choice.get("content")
        raw_tool_calls = choice.get("tool_calls", [])

        tool_calls: list[LLMToolCall] = []
        for tc in raw_tool_calls:
            fn = tc["function"]
            try:
                args = (
                    json.loads(fn["arguments"])
                    if isinstance(fn["arguments"], str)
                    else fn["arguments"]
                )
            except Exception:
                args = {}

            tool_calls.append(
                LLMToolCall(
                    id=tc["id"],
                    name=fn["name"],
                    arguments=args,
                )
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=data.get("model", self.model),
            provider="openai",
        )


def _format_tool_execution_response(raw_content: str) -> str:
    """Formats raw JSON tool execution payloads into natural agent prose."""
    try:
        parsed_res = json.loads(raw_content) if raw_content.startswith("{") else {}
    except Exception:
        parsed_res = {}

    if "catalog_items" in parsed_res:
        items_str = "\n".join(
            [
                f"• **{item['name']}** — {item['price_inr']} ({'In Stock' if item.get('in_stock') else 'Out of Stock'})"
                for item in parsed_res["catalog_items"]
            ]
        )
        return (
            f"Here are the available products in our verified catalog:\n\n{items_str}\n\n"
            "Let me know if you would like me to procure any of these items within my mandate bounds."
        )
    if parsed_res.get("policy_decision") == "ALLOW":
        prod = parsed_res.get("product") or "Item"
        op_id = parsed_res.get("operation_id")
        amt = parsed_res.get("amount_inr")
        return (
            f"✅ **Purchase Order Authorized!**\n\n"
            f"I have successfully created purchase order `{op_id}` for **{prod}** totaling **{amt}**.\n"
            f"Mandate's Deterministic Policy Gate approved the transaction and reserved the funds."
        )
    if parsed_res.get("policy_decision") == "DENY":
        prod = parsed_res.get("product") or "requested operation"
        err = parsed_res.get("error_message") or "Operation bounds exceeded"
        return (
            f"🛑 **Mandate Policy Blocked Action!**\n\n"
            f"I attempted to execute the request for **{prod}**, but Mandate's Policy Gate **DENIED** authorization:\n"
            f"> *{err}*\n\n"
            f"No Razorpay funds were disbursed."
        )
    return f"Operation evaluated by Mandate Control Plane:\n```json\n{raw_content}\n```"


def _parse_semantic_intent(user_text: str) -> list[LLMToolCall] | str:
    """Parses natural language prompt and returns tool call or friendly conversational reply."""
    # 1. Browse Catalog Intent
    if any(k in user_text for k in ["browse", "catalog", "products", "items", "list"]):
        return [
            LLMToolCall(
                id=f"call_browse_{uuid.uuid4().hex[:8]}",
                name="browse_catalog",
                arguments={},
            )
        ]

    # 2. Refund Intent
    if "refund" in user_text or "return" in user_text:
        amt = 2500 if "2,500" in user_text or "2500" in user_text else 1000
        return [
            LLMToolCall(
                id=f"call_rfnd_{uuid.uuid4().hex[:8]}",
                name="issue_customer_refund",
                arguments={
                    "payment_id": "pay_fake_attacker_01"
                    if "attacker" in user_text
                    else "pay_demo_legit_01",
                    "amount_in_rupees": amt,
                    "reason": "Customer request via playground",
                },
            )
        ]

    # 3. Order / Buy Intent
    if any(k in user_text for k in ["buy", "order", "procure", "purchase", "keyboard", "monitor"]):
        qty = 100 if "100" in user_text else 5 if "5" in user_text else 1
        prod_id = (
            "prod_monitor_high_end"
            if "monitor" in user_text or "dell" in user_text or "75,000" in user_text
            else "prod_kb_01"
        )
        return [
            LLMToolCall(
                id=f"call_order_{uuid.uuid4().hex[:8]}",
                name="create_purchase_order",
                arguments={
                    "product_id": prod_id,
                    "quantity": qty,
                    "customer_name": "Alice Developer",
                },
            )
        ]

    # 4. Payment Link Intent
    if "payment link" in user_text or "link" in user_text or "invoice" in user_text:
        return [
            LLMToolCall(
                id=f"call_plink_{uuid.uuid4().hex[:8]}",
                name="create_payment_link_for_customer",
                arguments={
                    "amount_in_rupees": 4500,
                    "description": "Mandate Invoice #1029",
                    "customer_name": "Client",
                },
            )
        ]

    # 5. Out-of-scope / Conversational Inquiries
    if any(w in user_text for w in ["ps5", "free", "million", "hello", "hi", "help", "who"]):
        return (
            "I am your bounded Mandate AI agent. I can only perform financial operations permitted "
            "under my cryptographic mandate (browsing catalog, purchasing approved items, creating invoices). "
            "I cannot disburse arbitrary funds, claim unauthorized inventory, or execute out-of-policy requests."
        )

    return (
        f'I understood your request: "{user_text}". However, no matching financial tool was triggered. '
        "You can ask me to browse the catalog, order an item (e.g. Keychron K2), or create a payment link."
    )


class MockLLMAdapter(BaseLLMAdapter):
    """Hermetic deterministic mock adapter with natural language intent parser for offline testing."""

    def __init__(
        self, predefined_tool_calls: list[LLMToolCall] | None = None, reply_text: str | None = None
    ) -> None:
        self.predefined_tool_calls = predefined_tool_calls or []
        self.reply_text = reply_text or "Simulated AI Agent Response"

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        # Check if last message is a tool response and format human-friendly agent reply
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            raw_content = str(last_msg.get("content", ""))
            return LLMResponse(
                content=_format_tool_execution_response(raw_content),
                tool_calls=[],
                model="mock-semantic-v1",
                provider="mock",
            )

        # If explicit predefined calls are set (e.g. in unit tests/eval harness)
        if self.predefined_tool_calls:
            return LLMResponse(
                content=None,
                tool_calls=self.predefined_tool_calls,
                model="mock-deterministic-v1",
                provider="mock",
            )

        # Natural Language Intent Parser for Interactive Agent Playground
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = str(m.get("content", "")).lower()
                break

        parsed = _parse_semantic_intent(user_text)
        if isinstance(parsed, list):
            return LLMResponse(
                content=None,
                tool_calls=parsed,
                model="mock-semantic-v1",
                provider="mock",
            )

        return LLMResponse(
            content=parsed,
            tool_calls=[],
            model="mock-semantic-v1",
            provider="mock",
        )


def get_llm_adapter(provider: str | None = None) -> BaseLLMAdapter:
    settings = get_settings()
    selected = (provider or settings.DEFAULT_LLM_PROVIDER).lower()

    if selected == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMAdapter()
    return MockLLMAdapter()
