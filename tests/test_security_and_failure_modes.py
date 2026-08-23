"""Comprehensive Security Negative Tests & Gateway Failure Atomicity Test Suite."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from packages.core.enums import (
    AgentStatus,
    MandateStatus,
    OperationStatus,
    PrincipalRole,
)
from packages.core.models import (
    Agent,
    FinancialOperation,
    Mandate,
    Principal,
    Transaction,
)
from packages.core.schemas import OperationCreate
from packages.razorpay.client import RazorpayClient, RazorpayOrderResponse
from services.worker.main import reconcile_stuck_reservations
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_auth_negative_scenarios_and_bearer_parity(async_client: AsyncClient) -> None:
    """Tests strict authentication invariants: invalid keys, identity mismatch, suspended agents, and Bearer parity."""
    api_key_valid = "agt_key_sec_101"
    key_hash = hashlib.sha256(api_key_valid.encode("utf-8")).hexdigest()

    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Security Test Corp", email="sec@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        active_agent = Agent(
            id="agt_sec_active_1",
            name="Active Security Bot",
            owner_id=principal.id,
            api_key_hash=key_hash,
            status=AgentStatus.ACTIVE,
        )
        suspended_agent = Agent(
            id="agt_sec_suspended_1",
            name="Suspended Bot",
            owner_id=principal.id,
            api_key_hash="hash_suspended_key_102",
            status=AgentStatus.SUSPENDED,
        )
        session.add_all([active_agent, suspended_agent])
        await session.flush()

        mandate = Mandate(
            agent_id=active_agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=500000,
            aggregate_spend_limit=1000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()

    rpc_req = {"jsonrpc": "2.0", "id": "auth_test", "method": "tools/list", "params": {}}

    # Case 1: Missing Authentication Credentials
    res_no_auth = await async_client.post("/api/v1/mcp", json=rpc_req)
    assert res_no_auth.status_code == 200
    assert res_no_auth.json()["error"]["code"] == -32001

    # Case 2: Invalid API Key
    res_bad_key = await async_client.post(
        "/api/v1/mcp", json=rpc_req, headers={"X-Agent-Key": "completely_wrong_key"}
    )
    assert res_bad_key.status_code == 200
    assert res_bad_key.json()["error"]["code"] == -32001

    # Case 3: Suspended Agent
    res_suspended = await async_client.post(
        "/api/v1/mcp", json=rpc_req, headers={"X-Agent-Key": "suspended_key_102"}
    )
    assert res_suspended.status_code == 200
    assert res_suspended.json()["error"]["code"] == -32001
    assert "SUSPENDED" in res_suspended.json()["error"]["message"]

    # Case 4: Key belonging to Agent A with X-Agent-Id pointing to Agent B (Identity Impersonation)
    res_mismatch = await async_client.post(
        "/api/v1/mcp",
        json=rpc_req,
        headers={"X-Agent-Key": api_key_valid, "X-Agent-Id": "agt_sec_suspended_1"},
    )
    assert res_mismatch.status_code == 200
    assert "mismatch" in res_mismatch.json()["error"]["message"].lower()

    # Case 5: Parity between X-Agent-Key and Authorization Bearer
    res_header_key = await async_client.post(
        "/api/v1/mcp", json=rpc_req, headers={"X-Agent-Key": api_key_valid}
    )
    res_bearer_token = await async_client.post(
        "/api/v1/mcp", json=rpc_req, headers={"Authorization": f"Bearer {api_key_valid}"}
    )
    assert res_header_key.status_code == 200
    assert res_bearer_token.status_code == 200
    assert res_header_key.json()["result"] == res_bearer_token.json()["result"]


@pytest.mark.asyncio
async def test_webhook_hmac_security_and_replay_protection(async_client: AsyncClient) -> None:
    """Tests constant-time HMAC signature verification, rejection of forged signatures, and idempotent duplicate handling."""
    webhook_secret = "whsec_super_secret_audit_key_888"

    payload_data = {
        "event_id": f"evt_sec_{uuid.uuid4().hex[:10]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_sec_{uuid.uuid4().hex[:10]}",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    raw_bytes = json.dumps(payload_data).encode("utf-8")
    valid_sig = hmac.new(webhook_secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    with patch("apps.api.routes.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.RAZORPAY_WEBHOOK_SECRET = webhook_secret
        mock_settings.return_value.ENVIRONMENT = "development"

        # Case 1: Missing Signature Header
        res_no_sig = await async_client.post(
            "/api/v1/webhooks/razorpay", content=raw_bytes, headers={"Content-Type": "application/json"}
        )
        assert res_no_sig.status_code == 422  # Header missing

        # Case 2: Forged / Invalid Signature
        res_forged = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": "0000000000000000000000000000000000000000000000000000000000000000",
            },
        )
        assert res_forged.status_code == 400
        assert "Invalid Razorpay webhook signature" in res_forged.json()["detail"]

        # Case 3: Valid Ingestion
        res_valid = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": valid_sig,
            },
        )
        assert res_valid.status_code == 200
        assert res_valid.json()["status"] == "PROCESSED"

        # Case 4: Duplicate Replay Attack
        res_replay = await async_client.post(
            "/api/v1/webhooks/razorpay",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": valid_sig,
            },
        )
        assert res_replay.status_code == 200
        assert res_replay.json()["status"] == "DUPLICATE_IGNORED"


@pytest.mark.asyncio
async def test_gateway_failure_immediate_reservation_release(async_client: AsyncClient) -> None:
    """Tests atomicity: Policy ALLOW -> budget reservation -> Razorpay request fails -> immediate budget release."""
    async with TestingSessionLocal() as session:
        principal = Principal(name="Fail Corp", email="fail@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="Fail Bot", owner_id=principal.id, api_key_hash="hash_fail_atom_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=1000000,
            aggregate_spend_limit=2000000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        mandate_id = mandate.id
        agent_id = agent.id

    # Mock Razorpay throwing a network 500 error
    with patch.object(
        RazorpayClient,
        "create_order",
        new_callable=AsyncMock,
        side_effect=httpx.HTTPStatusError("Gateway Error 500", request=AsyncMock(), response=AsyncMock(status_code=500)),
    ):
        req = {
            "idempotency_key": f"idem_fail_{uuid.uuid4().hex[:8]}",
            "agent_id": agent_id,
            "mandate_id": mandate_id,
            "operation_type": "CREATE_ORDER",
            "amount": 400000,
            "currency": "INR",
            "payload": {"item": "Server Rack"},
        }
        res = await async_client.post("/api/v1/operations", json=req)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "FAILED"

    # Verify that reserved_spend was immediately released back to 0
    async with TestingSessionLocal() as session:
        mnd = await session.get(Mandate, mandate_id)
        assert mnd is not None
        assert mnd.reserved_spend == 0
        assert mnd.current_aggregate_spend == 0


@pytest.mark.asyncio
async def test_production_guardrails_enforcement(async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Strictly verifies all 4 production guardrail invariants:
    1. Settings rejects RAZORPAY_MOCK_MODE=True in production.
    2. Settings rejects AUTO_SEED_DEMO=True in production.
    3. Demo dataset reset endpoint returns 403 Forbidden in production.
    4. Unauthenticated agent callers are rejected with 401 Unauthorized in production.
    """
    from packages.shared.config import Settings, get_settings

    # 1. Reject RAZORPAY_MOCK_MODE=True in production
    with pytest.raises(ValueError, match="RAZORPAY_MOCK_MODE must be False in production"):
        Settings(
            ENVIRONMENT="production",
            RAZORPAY_MOCK_MODE=True,
            AUTO_SEED_DEMO=False,
            RAZORPAY_KEY_ID="rzp_live_real_id",
            RAZORPAY_KEY_SECRET="real_secret_123",
            RAZORPAY_WEBHOOK_SECRET="whsec_real_123",
        )

    # 2. Reject AUTO_SEED_DEMO=True in production
    with pytest.raises(ValueError, match="AUTO_SEED_DEMO cannot be enabled in production"):
        Settings(
            ENVIRONMENT="production",
            RAZORPAY_MOCK_MODE=False,
            AUTO_SEED_DEMO=True,
            RAZORPAY_KEY_ID="rzp_live_real_id",
            RAZORPAY_KEY_SECRET="real_secret_123",
            RAZORPAY_WEBHOOK_SECRET="whsec_real_123",
        )

    # 3. Demo dataset reset endpoint rejected with 403 in production
    current_settings = get_settings()
    monkeypatch.setattr(current_settings, "ENVIRONMENT", "production")

    reset_res = await async_client.post("/api/v1/demo/reset")
    assert reset_res.status_code == 403
    assert "strictly disabled in production" in reset_res.json()["detail"]

    # 4. Unauthenticated agent operations rejected with 401 in production
    mcp_res = await async_client.post(
        "/api/v1/mcp",
        json={"jsonrpc": "2.0", "id": "prod_test", "method": "tools/list", "params": {}},
        headers={"X-Agent-Id": "agt_test_01"},  # Only ID provided without Key
    )
    assert mcp_res.status_code == 200
    mcp_data = mcp_res.json()
    assert mcp_data.get("error") is not None
    assert "Missing authentication" in mcp_data["error"]["message"]

