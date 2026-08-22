"""Automated Smoke Test verifying clean-slate reset and complete 5-minute showcase execution."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_competition_demo_smoke_suite(async_client: AsyncClient) -> None:
    """
    Smoke Test:
    Executes clean-slate reset followed by the 3 canonical acts of the 5-minute showcase journey,
    and validates the full end-to-end /demo/run-journey endpoint.
    """
    # 1. Reset Clean Slate
    reset_res = await async_client.post("/api/v1/demo/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "SUCCESS"
    assert reset_data["seeded_principal_id"] == "prn_alpha_corp_01"

    # 2. Act 1: Compliant Agent Commerce Journey -> ALLOW
    s1_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 1})
    assert s1_res.status_code == 200
    s1 = s1_res.json()
    assert s1["decision"] == "ALLOW"
    assert s1["authorized"] is True
    assert s1["gateway_calls_dispatched"] == 1
    assert "Razorpay Test Mode Order Created" in s1["gateway_effect"]
    assert len(s1["flow_steps"]) >= 6

    # 3. Act 2: Adversarial Bulk Escalation Attack Blocked -> DENY (0 Gateway Calls)
    s2_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 2})
    assert s2_res.status_code == 200
    s2 = s2_res.json()
    assert s2["decision"] == "DENY"
    assert s2["authorized"] is False
    assert s2["gateway_calls_dispatched"] == 0
    assert "0 Razorpay Calls Dispatched" in s2["gateway_effect"]

    # 4. Act 3: Webhook Failure & Self-Healing Reconciliation -> RECONCILED
    s3_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 3})
    assert s3_res.status_code == 200
    s3 = s3_res.json()
    assert s3["decision"] == "RECONCILED"
    assert s3["authorized"] is True
    assert s3["gateway_calls_dispatched"] == 1
    assert "Reconciled" in s3["gateway_effect"]

    # 5. Full End-to-End Showcase Runner (/demo/run-journey)
    journey_res = await async_client.post("/api/v1/demo/run-journey")
    assert journey_res.status_code == 200
    jdata = journey_res.json()
    assert jdata["status"] == "SUCCESS"
    assert jdata["total_acts"] == 3
    assert len(jdata["journey_steps"]) == 3
    assert jdata["total_gateway_calls"] == 2  # Act 1 (1) + Act 2 (0) + Act 3 (1)

