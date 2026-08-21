"""Tests for Event Bus and event schemas."""

import pytest

from packages.core.enums import AuditAction
from packages.events.bus import AuditLogEvent, InMemoryEventBus


@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe() -> None:
    bus = InMemoryEventBus()
    received_events = []

    async def sample_handler(event: AuditLogEvent) -> None:
        received_events.append(event)

    bus.subscribe("audit", sample_handler)

    evt = AuditLogEvent(
        action=AuditAction.AGENT_REGISTERED,
        actor_id="usr_admin",
        actor_type="PRINCIPAL",
        resource_id="agent_123",
        resource_type="AGENT",
        payload={"name": "Procurement Bot"},
    )

    await bus.publish("audit", evt)
    assert len(received_events) == 1
    assert received_events[0].resource_id == "agent_123"
    assert received_events[0].action == AuditAction.AGENT_REGISTERED
