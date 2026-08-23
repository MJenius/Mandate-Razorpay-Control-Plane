"""Run with AGENT_ID and MANDATE_ID set for a safe, pre-provisioned test mandate."""

import os
import uuid

from locust import HttpUser, between, task


class MandateUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def create_order(self) -> None:
        self.client.post(
            "/api/v1/operations",
            json={
                "idempotency_key": f"load-{uuid.uuid4()}",
                "agent_id": os.environ["AGENT_ID"],
                "mandate_id": os.environ["MANDATE_ID"],
                "operation_type": "CREATE_ORDER",
                "amount": int(os.getenv("AMOUNT", "100")),
                "currency": "INR",
                "payload": {},
            },
            name="shared-mandate-order",
        )
