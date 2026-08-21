"""Event schemas and async event bus abstractions."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from packages.core.enums import AuditAction


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseEvent(BaseModel):
    """Base schema for domain & audit events."""
    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    timestamp: datetime = Field(default_factory=utc_now)
    source_service: str = "mandate-api"


class FinancialOperationEvent(BaseEvent):
    """Event emitted when a financial operation undergoes a lifecycle change."""
    operation_id: str
    idempotency_key: str
    agent_id: str
    mandate_id: str
    operation_type: str
    status: str
    amount: int
    currency: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLogEvent(BaseEvent):
    """Immutable audit trail event."""
    action: AuditAction
    actor_id: str
    actor_type: str
    resource_id: str
    resource_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None


EventHandler = Callable[[BaseEvent], Coroutine[Any, Any, None]]


class EventBus(ABC):
    """Abstract interface for event publishing and subscribing."""

    @abstractmethod
    async def publish(self, topic: str, event: BaseEvent) -> None:
        pass

    @abstractmethod
    def subscribe(self, topic: str, handler: EventHandler) -> None:
        pass


class InMemoryEventBus(EventBus):
    """In-memory event bus implementation for Phase 0 and unit tests."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self.published_events: List[BaseEvent] = []

    async def publish(self, topic: str, event: BaseEvent) -> None:
        self.published_events.append(event)
        if topic in self._handlers:
            for handler in self._handlers[topic]:
                await handler(event)

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)
