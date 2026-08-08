import json

import redis.asyncio as aioredis

from app.common.config import settings

# redis-py's from_url() automatically handles:
#   rediss:// → TLS enabled
#   redis://  → plain (local dev)
# The password is embedded in the REDIS_URL for Upstash.
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
    # Upstash TLS: skip cert verification (avoids SSL errors on some hosts)
    ssl_cert_reqs=None,
)


def get_redis_client() -> aioredis.Redis:
    """
    Returns an async Redis client from pool.
    Works with both local Redis and Upstash (TLS).
    """
    return aioredis.Redis(connection_pool=redis_pool)


async def publish_job_progress(
    job_id: str, progress_percent: int, status: str, detail: str = ""
) -> None:
    """
    Publishes job progress update to Redis PubSub channel 'job_progress:{job_id}'.
    Frontend subscribes to this channel for real-time render progress.
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
