import asyncio
import json
import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.config import settings
from app.common.db import get_async_session
from app.common.redis import get_redis_client
from app.common.security import get_current_user
from app.storage.service import storage_service
from app.users.model import User
from app.videos.model import JobStatus, VideoJob
from app.videos.schema import (
    VideoJobResponse,
    VideoJobStatusResponse,
    VideoRenderRequest,
)

router = APIRouter(tags=["Videos & Progress Streams"])


@router.post(
    "/videos/render",
    response_model=VideoJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue video render job",
)
async def enqueue_video_render(
    request: VideoRenderRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    new_job = VideoJob(
        user_id=current_user.id,
        status=JobStatus.QUEUED,
        progress_percent=0,
        script_json=request.script_json.model_dump(),
        background_asset_id=request.background_asset_id,
        voice_id=request.voice_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    try:
        redis_arq = await create_pool(
            RedisSettings(
                host=settings.REDIS_HOST, port=settings.REDIS_PORT
            )
        )
        await redis_arq.enqueue_job(
            "process_video_render_job", str(new_job.id)
        )
    except Exception as e:
        print(
            f"[ARQ Queue Warning] Could not enqueue job to Redis worker: {e}"
        )

    return VideoJobResponse(
        job_id=new_job.id,
        status=new_job.status,
        progress_percent=new_job.progress_percent,
        message="Video render task enqueued to Redis background queue.",
    )


@router.get(
    "/videos/jobs/{job_id}",
    response_model=VideoJobStatusResponse,
    summary="Poll video job status & presigned Cloudflare R2 download link",
)
async def get_job_status(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(VideoJob).where(VideoJob.id == job_id)
    res = await session.exec(stmt)
    job = res.first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video job '{job_id}' not found.",
        )

    download_url = None
    if job.status == JobStatus.COMPLETED and job.output_video_url:
        r2_key = f"renders/{job.id}.mp4"
        download_url = await storage_service.generate_presigned_url(
            r2_key=r2_key, expiration_seconds=3600
        )

    return VideoJobStatusResponse(
        id=job.id,
        user_id=job.user_id,
        status=job.status,
        progress_percent=job.progress_percent,
        audio_url=job.audio_url,
        output_video_url=job.output_video_url,
        download_url=download_url,
        error_message=job.error_message,
        created_at=job.created_at,
    )


@router.get(
    "/videos/jobs/{job_id}/stream",
    summary="Server-Sent Events (SSE) stream for live render progress",
)
async def job_progress_sse(job_id: str):
    async def event_generator():
        init_msg = json.dumps({"event": "connected", "job_id": job_id})
        yield f"data: {init_msg}\n\n"
        try:
            redis_client = get_redis_client()
            pubsub = redis_client.pubsub()
            channel_name = f"job_progress:{job_id}"
            await pubsub.subscribe(channel_name)

            try:
                loop_count = 0
                while loop_count < 10:
                    loop_count += 1
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=0.5
                    )
                    if message and message.get("type") == "message":
                        data_str = message.get("data")
                        if data_str:
                            yield f"data: {data_str}\n\n"
                            try:
                                data_json = json.loads(data_str)
                                status = data_json.get("status")
                                if status in ["COMPLETED", "FAILED"]:
                                    break
                            except Exception:
                                pass
                    await asyncio.sleep(0.1)
            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
        except Exception as e:
            print(
                f"[SSE Warning] Could not connect to Redis PubSub ({e})"
            )
            yield f"data: {json.dumps({'event': 'disconnected', 'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream"
    )
