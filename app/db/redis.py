from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

# Built from explicit kwargs, not a URL string — a password with URL-special
# characters (as managed providers like Railway generate) would otherwise need
# careful percent-encoding to survive round-tripping through Redis.from_url().
redis_client: Redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
)


def get_redis() -> Redis:
    return redis_client
