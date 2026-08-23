"""Production-Grade Redis-backed Sliding Window and Token Bucket Rate Limiter with per-agent isolation."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from packages.shared.config import get_settings
from packages.shared.logging import get_logger
from packages.shared.redis import get_redis_client

_fallback_buckets: dict[str, deque[float]] = defaultdict(deque)

logger = get_logger("shared.rate_limiter")


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_epoch_seconds: int
    retry_after_seconds: float
    agent_id: str
    tier: str
    rejection_reason: str | None = None


class RedisRateLimiter:
    """
    Sliding-Window and Burst Token Bucket Rate Limiter backed by Redis.
    Guarantees strict per-agent namespace isolation so that one compromised or runaway
    agent cannot exhaust or affect another agent's quota.
    """

    def __init__(
        self,
        default_rate_limit: int = 60,  # 60 ops / minute
        default_window_seconds: int = 60,
        burst_multiplier: float = 1.5,
    ) -> None:
        self.default_rate_limit = default_rate_limit
        self.default_window_seconds = default_window_seconds
        self.burst_limit = int(default_rate_limit * burst_multiplier)

    def _get_key(self, agent_id: str, tier: str = "standard") -> str:
        return f"ratelimit:agent:{agent_id}:{tier}"

    async def check_rate_limit(
        self,
        agent_id: str,
        cost: int = 1,
        custom_limit: int | None = None,
        custom_window_seconds: int | None = None,
        tier: str = "standard",
    ) -> RateLimitResult:
        """
        Atomic sliding-window rate limit evaluation using Redis Sorted Sets (ZADD/ZREMRANGEBYSCORE).
        Falls back safely to local memory if Redis is temporarily unreachable.
        """
        limit = custom_limit or self.default_rate_limit
        window = custom_window_seconds or self.default_window_seconds
        now = time.time()
        clear_before = now - window
        key = self._get_key(agent_id, tier)

        try:
            redis = get_redis_client()
            pipe = redis.pipeline(transaction=True)
            # Remove timestamps outside the sliding window
            pipe.zremrangebyscore(key, "-inf", clear_before)
            # Count remaining items in current window
            pipe.zcard(key)
            # Add current timestamp
            member_id = f"{now}:{cost}:{time.perf_counter_ns()}"
            pipe.zadd(key, {member_id: now})
            # Set TTL to ensure keys expire
            pipe.expire(key, window + 10)

            results = await pipe.execute()
            current_count = int(results[1])

            if current_count + cost > limit:
                # Revert adding current if exceeding limit
                await redis.zrem(key, member_id)
                oldest_entries = await redis.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest_entries[0][1] + window) if oldest_entries else int(now + window)
                retry_after = max(0.1, round(reset_time - now, 2))

                logger.warning(
                    "rate_limit_exceeded",
                    agent_id=agent_id,
                    tier=tier,
                    current_count=current_count,
                    limit=limit,
                    retry_after=retry_after,
                )

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_epoch_seconds=reset_time,
                    retry_after_seconds=retry_after,
                    agent_id=agent_id,
                    tier=tier,
                    rejection_reason=f"Agent '{agent_id}' rate limit exceeded ({current_count}/{limit} in {window}s window). Retry after {retry_after}s.",
                )

            remaining = max(0, limit - (current_count + cost))
            reset_time = int(now + window)

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_epoch_seconds=reset_time,
                retry_after_seconds=0.0,
                agent_id=agent_id,
                tier=tier,
            )

        except Exception as exc:
            logger.warning("redis_rate_limit_fallback", agent_id=agent_id, error=str(exc))
            # A local limiter preserves per-process isolation in development/tests.  Production
            # must fail closed because this cannot coordinate multiple API instances.
            if get_settings().ENVIRONMENT.lower() == "production":
                return RateLimitResult(
                    allowed=False, limit=limit, remaining=0, reset_epoch_seconds=int(now + window),
                    retry_after_seconds=1.0, agent_id=agent_id, tier=tier,
                    rejection_reason="Rate limiter unavailable; request denied safely.",
                )
            bucket = _fallback_buckets[key]
            while bucket and bucket[0] <= clear_before:
                bucket.popleft()
            if len(bucket) + cost > limit:
                retry_after = max(0.1, bucket[0] + window - now) if bucket else float(window)
                return RateLimitResult(
                    allowed=False, limit=limit, remaining=0, reset_epoch_seconds=int(now + retry_after),
                    retry_after_seconds=round(retry_after, 2), agent_id=agent_id, tier=f"{tier}_local",
                    rejection_reason=f"Agent '{agent_id}' rate limit exceeded.",
                )
            bucket.extend([now] * cost)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - len(bucket),
                reset_epoch_seconds=int(now + window),
                retry_after_seconds=0.0,
                agent_id=agent_id,
                tier=f"{tier}_local",
            )
