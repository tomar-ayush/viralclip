from arq.connections import RedisSettings
from app.common.config import settings
from app.videos.tasks import process_video_render_job


def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )


class WorkerSettings:
    functions = [process_video_render_job]
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 600
