from arq.connections import RedisSettings

from app.common.config import settings
from app.videos.tasks import process_video_render_job


def get_redis_settings() -> RedisSettings:
    """
    Build ARQ RedisSettings from REDIS_URL env var.
    Supports both:
      - Local:   redis://localhost:6379/0
      - Upstash: rediss://default:PASSWORD@host:6379  (TLS required)
    """
    use_ssl = settings.REDIS_URL.startswith("rediss://")
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        ssl=use_ssl,                  # True for Upstash (TLS), False for local
    )


class WorkerSettings:
    functions = [process_video_render_job]  # noqa: RUF012
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 600
