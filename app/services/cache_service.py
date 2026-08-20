import hashlib
import json
from typing import Any

from redis.asyncio import Redis

DASHBOARD_STATS_KEY = "cache:dashboard:stats"
DASHBOARD_STATS_TTL_SECONDS = 60

TICKET_LIST_PREFIX = "cache:tickets:list:"
TICKET_LIST_TTL_SECONDS = 30


def build_ticket_list_cache_key(**parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{TICKET_LIST_PREFIX}{digest}"


async def get_cached(redis: Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return json.loads(raw) if raw is not None else None


async def set_cached(redis: Redis, key: str, value: Any, ttl_seconds: int) -> None:
    await redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def invalidate_ticket_caches(redis: Redis) -> None:
    """Called after any ticket write. Wipes the dashboard stats cache and every
    cached ticket-list variant, rather than trying to compute which specific
    filter/page combinations are now stale."""
    await redis.delete(DASHBOARD_STATS_KEY)
    async for key in redis.scan_iter(match=f"{TICKET_LIST_PREFIX}*"):
        await redis.delete(key)
