from unittest.mock import patch

import pytest

from packages.shared.rate_limiter import RedisRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_keeps_agent_quotas_isolated_when_redis_is_down() -> None:
    limiter = RedisRateLimiter(default_rate_limit=2, default_window_seconds=60)
    with patch("packages.shared.rate_limiter.get_redis_client", side_effect=OSError("offline")):
        assert (await limiter.check_rate_limit("agent-a")).allowed
        assert (await limiter.check_rate_limit("agent-a")).allowed
        assert not (await limiter.check_rate_limit("agent-a")).allowed
        assert (await limiter.check_rate_limit("agent-b")).allowed
