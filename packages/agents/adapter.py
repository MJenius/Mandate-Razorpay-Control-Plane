"""Multi-provider LLM Adapter supporting OpenAI, mock hermetic runner, and future providers."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field
from packages.shared.config import get_settings
from packages.shared.logging import get_logger

logger = get_logger("agents.adapter")


class LLMToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[LLMToolCall] = Field(default_factory=list)
    model: str
    provider: str


class BaseLLMAdapter(ABC):
    """Abstract base adapter for LLM tool-calling backends."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass


class OpenAILLMAdapter(BaseLLMAdapter):
    """OpenAI API implementation for structured tool calling."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured in environment")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        content = choice.get("content")
        raw_tool_calls = choice.get("tool_calls", [])

        tool_calls: List[LLMToolCall] = []
        for tc in raw_tool_calls:
            fn = tc["function"]
            try:
                args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
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


class MockLLMAdapter(BaseLLMAdapter):
    """Hermetic deterministic mock adapter for offline automated tests."""

    def __init__(self, predefined_tool_calls: Optional[List[LLMToolCall]] = None, reply_text: Optional[str] = None) -> None:
        self.predefined_tool_calls = predefined_tool_calls or []
        self.reply_text = reply_text or "Simulated AI Agent Response"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        # Check if last message is a tool response
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            return LLMResponse(
                content=f"Operation processed. Result: {last_msg.get('content')}",
                tool_calls=[],
                model="mock-deterministic-v1",
                provider="mock",
            )

        return LLMResponse(
            content=self.reply_text if not self.predefined_tool_calls else None,
            tool_calls=self.predefined_tool_calls,
            model="mock-deterministic-v1",
            provider="mock",
        )


def get_llm_adapter(provider: Optional[str] = None) -> BaseLLMAdapter:
    settings = get_settings()
    selected = (provider or settings.DEFAULT_LLM_PROVIDER).lower()

    if selected == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMAdapter()
    return MockLLMAdapter()
