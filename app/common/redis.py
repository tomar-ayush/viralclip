import json

import redis.asyncio as aioredis

from app.common.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL, decode_responses=True, max_connections=20
)


def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client from pool.
    """
    return aioredis.Redis(connection_pool=redis_pool)


async def publish_job_progress(
    job_id: str, progress_percent: int, status: str, detail: str = ""
) -> None:
    """
    Publishes job progress update to Redis PubSub channel 'job_progress:{job_id}'.
    """
    try:
        client = get_redis_client()
        channel = f"job_progress:{job_id}"
        message = json.dumps(
            {
                "job_id": job_id,
                "progress_percent": progress_percent,
                "status": status,
                "detail": detail,
            }
        )
        await client.publish(channel, message)
    except Exception as e:
        print(f"[Redis Warning] Could not publish job progress: {e}")
