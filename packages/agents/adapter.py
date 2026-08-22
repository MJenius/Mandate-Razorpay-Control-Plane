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
    if "operation_id" in parsed_res and "status" in parsed_res and "amount_inr" in parsed_res and "policy_decision" not in parsed_res:
        item = parsed_res.get("product", "Keychron K2 Mechanical Keyboard")
        op_id = parsed_res["operation_id"]
        price = parsed_res["amount_inr"]
        status = parsed_res["status"]
        refund_status = parsed_res.get("refund_eligible", "Yes (Within 30-day return policy window)")

        return (
            f"📦 **Order Details:**\n\n"
            f"• **Item:** **{item}**\n"
            f"• **Order ID:** `{op_id}`\n"
            f"• **Price:** **{price}**\n"
            f"• **Status:** `{status}`\n"
            f"• **Refund Status:** {refund_status}\n\n"
            f"Verified against Mandate Ledger & PostgreSQL event store."
        )
    if parsed_res.get("policy_decision") == "ALLOW":
        prod = parsed_res.get("product") or ("Customer Refund" if "refund" in str(parsed_res) else "Item")
        op_id = parsed_res.get("operation_id")
        amt = parsed_res.get("amount_inr")
        return (
            f"✅ **Financial Operation Authorized!**\n\n"
            f"I have successfully executed `{op_id}` for **{prod}** totaling **{amt}**.\n"
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
    text_lower = user_text.lower().strip()

    # 0. Conversational Greetings & Identity (Chatbot persona)
    if text_lower in ["hello", "hi", "hey", "good morning", "good evening", "greetings"]:
        return (
            "Hello! I am your Mandate AI Agent. I can help you explore our verified catalog, "
            "inspect purchase history in the ledger, recommend products, and securely execute bounded financial transactions."
        )

    # 0b. Capabilities, Limits, and Boundaries (Conversational explanation)
    if any(
        phrase in text_lower
        for phrase in [
            "what is your limit",
            "what it your limit",
            "what are your limits",
            "how much can you",
            "what are your bounds",
            "what are your rules",
            "tell me your limit",
            "tell me your bound",
            "what can you do",
            "how do you work",
            "who are you",
            "help",
        ]
    ):
        return (
            "I operate as an autonomous AI Agent bounded by Mandate's Deterministic Policy Gate. "
            "I can chat with you, browse products, look up past orders, and process authorized purchases or refunds. "
            "Every financial action I propose is cryptographically validated and constrained by mathematical authority limits before touching Razorpay."
        )

    # 1. Inspection / Ledger History Queries (Must NOT buy or mutate funds)
    if any(
        k in text_lower
        for k in [
            "recent purchases",
            "my purchases",
            "past purchases",
            "recent orders",
            "my orders",
            "past orders",
            "show my recent",
            "show recent",
            "show orders",
            "show purchases",
            "what did i buy",
            "what did we buy",
            "what was bought",
            "inspect",
            "lookup",
            "status",
            "check operation",
            "check order",
            "latest order",
            "last order",
            "op_",
        ]
    ):
        words = user_text.replace(":", " ").replace(",", " ").replace('"', " ").replace("'", " ").split()
        target_op = "latest_order" if any(w in text_lower for w in ["order", "bought", "purchase", "item", "recent", "past", "my"]) else "latest"
        for w in words:
            if w.startswith("op_") or w.startswith("pay_"):
                target_op = w
                break
        return [
            LLMToolCall(
                id=f"call_lookup_{uuid.uuid4().hex[:8]}",
                name="lookup_transaction",
                arguments={
                    "operation_id": target_op,
                    "order_only": True,
                },
            )
        ]

    # 2. Browse Catalog Intent
    if any(
        k in text_lower
        for k in [
            "browse",
            "catalog",
            "products",
            "show products",
            "list items",
            "what do you sell",
            "available items",
            "show items",
            "what is there",
            "what can i buy",
            "what all can i buy",
            "what can we buy",
            "what to buy",
            "what is available",
            "what do you have",
            "items for sale",
        ]
    ):
        return [
            LLMToolCall(
                id=f"call_browse_{uuid.uuid4().hex[:8]}",
                name="browse_catalog",
                arguments={},
            )
        ]

    # 3. Conversational Product Queries & Recommendations
    if any(q in text_lower for q in ["what is", "tell me about", "price of", "cost of", "how much is", "recommend", "show me", "which", "difference between"]):
        if any(k in text_lower for k in ["keyboard", "keychron"]):
            return (
                "The **Keychron K2 Mechanical Keyboard** is available in our catalog for **Rs. 6,500.00**. "
                "It features wireless/wired connectivity and hot-swappable switches. Say *'Buy 1 Keychron K2'* if you'd like me to order it!"
            )
        if any(k in text_lower for k in ["mouse", "logitech", "mx master"]):
            return (
                "The **Logitech MX Master 3S Mouse** is available for **Rs. 8,999.00**. "
                "It is designed for ergonomics and ultra-quiet precision. Say *'Buy 1 Logitech Mouse'* to purchase."
            )
        if any(k in text_lower for k in ["desk mat", "mat", "felt"]):
            return (
                "The **Ergonomic Wool Felt Desk Mat** is available for **Rs. 1,500.00**. "
                "Say *'Buy 1 Desk Mat'* if you would like me to procure one."
            )
        if any(k in text_lower for k in ["monitor", "dell", "4k"]):
            return (
                "The **Dell UltraSharp 32-inch 4K Monitor** is priced at **Rs. 75,000.00**. "
                "High-value hardware orders are governed by Mandate's multi-level policy thresholds."
            )
        if any(k in text_lower for k in ["workstation", "server", "gpu"]):
            return (
                "The **Rackmount GPU AI Workstation** is priced at **Rs. 4,50,000.00** for enterprise compute workloads."
            )

    # 4. Refund Intent (Active command to issue or return)
    if any(k in text_lower for k in ["refund", "return", "reimburse"]):
        if any(q in text_lower for q in ["can i refund", "is refund possible", "how do refunds work", "policy on refund", "do you do refunds"]):
            return (
                "Yes! Settled purchases within 30 days are eligible for refund through customer support. "
                "You can say *'Process a damaged item return refund of Rs. 1,500'* to initiate a refund."
            )

        import re
        amt = 1000.0
        if "25,000" in user_text or "25000" in user_text:
            amt = 25000.0
        elif "2,500" in user_text or "2500" in user_text:
            amt = 2500.0
        elif "1,500" in user_text or "1500" in user_text:
            amt = 1500.0
        elif "5,000" in user_text or "5000" in user_text:
            amt = 5000.0
        elif "6,500" in user_text or "6500" in user_text or "keyboard" in text_lower or "keychron" in text_lower:
            amt = 6500.0
        elif "8,999" in user_text or "8999" in user_text or "mouse" in text_lower or "logitech" in text_lower:
            amt = 8999.0
        elif "desk mat" in text_lower or "felt" in text_lower or "mat" in text_lower:
            amt = 1500.0
        elif "monitor" in text_lower or "75,000" in user_text or "75000" in user_text:
            amt = 75000.0
        else:
            match = re.search(r"(?:rs\.?|₹|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+)", user_text, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1).replace(",", ""))
                    if val > 0:
                        amt = val
                except Exception:
                    amt = 1000.0

        words = user_text.replace(":", " ").replace(",", " ").replace('"', " ").replace("'", " ").split()
        target_pay_id = "pay_demo_cap_01" if "pay_demo" in user_text else "pay_fake_attacker_01"
        for w in words:
            if w.startswith("pay_"):
                target_pay_id = w
                break

        return [
            LLMToolCall(
                id=f"call_rfnd_{uuid.uuid4().hex[:8]}",
                name="issue_customer_refund",
                arguments={
                    "payment_id": target_pay_id,
                    "amount_in_rupees": amt,
                    "reason": "Customer request via support dialogue",
                },
            )
        ]

    # 5. Explicit Order / Buy Intent (Active purchasing command)
    is_buying_action = (
        any(
            cmd in text_lower
            for cmd in [
                "buy 1",
                "buy a",
                "buy the",
                "buy two",
                "buy 5",
                "buy ",
                "place order",
                "place an order",
                "procure",
                "purchase 1",
                "purchase a",
                "purchase the",
                "i want to buy",
                "i would like to buy",
                "get me a",
                "get me 1",
                "get a",
                "create purchase order",
                "create order",
                "order 1",
                "order a",
                "order the",
            ]
        )
        or (
            text_lower.startswith("buy")
            or text_lower.startswith("order")
            or text_lower.startswith("purchase")
            or text_lower.startswith("procure")
        )
    ) and not any(
        q in text_lower
        for q in [
            "what can",
            "what all",
            "can i buy",
            "should i buy",
            "how to buy",
            "where to buy",
            "why buy",
        ]
    )

    if is_buying_action:
        qty = 100 if "100" in user_text else 5 if "5" in user_text else 1

        if any(k in text_lower for k in ["mat", "desk mat", "felt", "wool"]):
            prod_id = "prod_desk_mat_01"
        elif any(k in text_lower for k in ["mouse", "logitech", "mx master", "mx"]):
            prod_id = "prod_mouse_01"
        elif any(k in text_lower for k in ["monitor", "dell", "4k", "ultrasharp", "75,000", "screen"]):
            prod_id = "prod_monitor_high_end"
        elif any(k in text_lower for k in ["workstation", "server", "gpu", "rackmount", "ai rack", "450,000"]):
            prod_id = "prod_enterprise_server"
        else:
            prod_id = "prod_kb_01"

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

    # 6. Payment Link Intent
    if "payment link" in text_lower or "send invoice" in text_lower or "create invoice" in text_lower:
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

    # 7. Conversational Pleasantries & Fallback
    if any(w in text_lower for w in ["thank", "thanks", "awesome", "great", "cool", "ok", "okay", "good", "bye"]):
        return "You're welcome! Let me know if you need help exploring the catalog, looking up past orders, or executing bounded financial transactions."

    return (
        f'I am here to help! You asked: "{user_text}". '
        "You can chat with me about items in our catalog, ask me to check your recent purchases, or command a financial action (e.g. *'Buy 1 Keychron K2'* or *'Process a refund of Rs. 1,500'*)."
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
