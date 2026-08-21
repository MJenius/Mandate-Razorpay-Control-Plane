"""Asynchronous background worker service for async operation execution."""

import asyncio
import signal
from typing import Any
from packages.events.bus import BaseEvent, InMemoryEventBus
from packages.shared.config import get_settings
from packages.shared.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("services.worker")

event_bus = InMemoryEventBus()


async def process_financial_operation_event(event: BaseEvent) -> None:
    """Handles async execution of policy-approved financial operations."""
    logger.info("worker_received_event", event_id=event.event_id, source=event.source_service)
    # Stub: Phase 1 will invoke Razorpay client to dispatch orders/transfers


class MandateWorker:
    """Async worker loop handling queue events and background reconciliations."""

    def __init__(self) -> None:
        self.running = False
        self.settings = get_settings()

    async def start(self) -> None:
        self.running = True
        logger.info("mandate_worker_started", concurrency=4)
        event_bus.subscribe("financial_operations", process_financial_operation_event)

        while self.running:
            try:
                # Worker heartbeat / polling loop
                await asyncio.sleep(5)
                logger.debug("worker_heartbeat_tick")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("worker_loop_error", error=str(e))
                await asyncio.sleep(1)

        logger.info("mandate_worker_stopped")

    def stop(self) -> None:
        self.running = False


async def main() -> None:
    worker = MandateWorker()
    
    # Graceful shutdown handler
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            pass  # Windows event loop fallback

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
