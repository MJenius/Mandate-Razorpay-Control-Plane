"""Automated Smoke Test verifying clean-slate reset and complete 5-minute showcase execution."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_competition_demo_smoke_suite(async_client: AsyncClient) -> None:
    """
    Smoke Test:
    Executes clean-slate reset followed by all 5 scripted competition showcase steps,
    guaranteeing 100% repeatability for live judging sessions.
    """
    # 1. Reset Clean Slate
    reset_res = await async_client.post("/api/v1/demo/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "SUCCESS"
    assert reset_data["seeded_principal_id"] == "prn_alpha_corp_01"

    # 2. Step 1: Legitimate Buyer Purchase -> ALLOW
    s1_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 1})
    assert s1_res.status_code == 200
    s1 = s1_res.json()
    assert s1["decision"] == "ALLOW"
    assert s1["authorized"] is True
    assert "Razorpay Test Mode Order Created" in s1["gateway_effect"]

    # 3. Step 2: Overreaching Bulk Order Attack -> DENY
    s2_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 2})
    assert s2_res.status_code == 200
    s2 = s2_res.json()
    assert s2["decision"] == "DENY"
    assert s2["authorized"] is False
    assert "0 Razorpay Calls Dispatched" in s2["gateway_effect"]

    # 4. Step 3: Compromised Cross-Role Refund Attack -> DENY
    s3_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 3})
    assert s3_res.status_code == 200
    s3 = s3_res.json()
    assert s3["decision"] == "DENY"
    assert s3["authorized"] is False

    # 5. Step 4: Webhook Auto-Convergence -> SETTLED
    s4_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 4})
    assert s4_res.status_code == 200
    s4 = s4_res.json()
    assert s4["decision"] == "SETTLED"

    # 6. Step 5: Cascading Parent Revocation -> REVOKED
    s5_res = await async_client.post("/api/v1/demo/run-scenario", json={"step_number": 5})
    assert s5_res.status_code == 200
    s5 = s5_res.json()
    assert s5["decision"] == "REVOKED"
    assert s5["details"]["child_status"] == "REVOKED"
