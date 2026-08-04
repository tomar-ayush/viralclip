import json
import asyncio
import uuid
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.db import get_async_session
from app.common.redis import get_redis_client
from app.users.model import User
from app.storage.service import storage_service
from app.videos.model import VideoJob, JobStatus
from app.videos.schema import VideoRenderRequest, VideoJobResponse, VideoJobStatusResponse

router = APIRouter(tags=["Videos & Progress Stream"])


@router.post("/videos/render", response_model=VideoJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Enqueue video render job")
async def enqueue_video_render(
    request: VideoRenderRequest,
    session: AsyncSession = Depends(get_async_session)
):
    user_stmt = select(User).where(User.id == request.user_id)
    user_res = await session.exec(user_stmt)
    if not user_res.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{request.user_id}' not found."
        )

    new_job = VideoJob(
        user_id=request.user_id,
        status=JobStatus.QUEUED,
        progress_percent=0,
        script_json=request.script_json.model_dump(),
        background_asset_id=request.background_asset_id,
        voice_id=request.voice_id
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    try:
        redis_arq = await create_pool(RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT))
        await redis_arq.enqueue_job("process_video_render_job", str(new_job.id))
    except Exception as e:
        print(f"[ARQ Queue Warning] Could not enqueue job to Redis worker: {e}")

    return VideoJobResponse(
        job_id=new_job.id,
        status=new_job.status,
        progress_percent=new_job.progress_percent,
        message="Video render task enqueued to Redis background queue."
    )


@router.get("/videos/jobs/{job_id}", response_model=VideoJobStatusResponse, summary="Poll video job status & presigned S3 download link")
async def get_job_status(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(VideoJob).where(VideoJob.id == job_id)
    res = await session.exec(stmt)
    job = res.first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video job '{job_id}' not found."
        )

    download_url = None
    if job.status == JobStatus.COMPLETED and job.output_video_url:
        s3_key = f"renders/{job.id}.mp4"
        download_url = await storage_service.generate_presigned_url(s3_key=s3_key, expiration_seconds=3600)

    return VideoJobStatusResponse(
        id=job.id,
        user_id=job.user_id,
        status=job.status,
        progress_percent=job.progress_percent,
        audio_url=job.audio_url,
        output_video_url=job.output_video_url,
        download_url=download_url,
        error_message=job.error_message,
        created_at=job.created_at
    )


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    channel_name = f"job_progress:{job_id}"

    try:
        await pubsub.subscribe(channel_name)
        await websocket.send_json({
            "event": "subscribed",
            "job_id": job_id,
            "message": f"Subscribed to real-time progress stream for job {job_id}"
        })

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data_str = message.get("data")
                if data_str:
                    await websocket.send_text(data_str)
                    try:
                        data_json = json.loads(data_str)
                        status = data_json.get("status")
                        if status in ["COMPLETED", "FAILED"]:
                            await asyncio.sleep(0.5)
                            await websocket.close(code=1000, reason=f"Job status: {status}")
                            break
                    except Exception:
                        pass
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
