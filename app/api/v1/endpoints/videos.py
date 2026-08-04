import uuid
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_async_session
from app.models.user import User
from app.models.video_job import VideoJob, JobStatus
from app.schemas.video import VideoRenderRequest, VideoJobResponse, VideoJobStatusResponse
from app.services.s3_service import s3_service

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/render", response_model=VideoJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Enqueue video render job")
async def enqueue_video_render(
    request: VideoRenderRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Creates a new VideoJob in QUEUED status and dispatches render task to Redis ARQ worker queue.
    """
    # 1. Verify user
    user_stmt = select(User).where(User.id == request.user_id)
    user_res = await session.exec(user_stmt)
    if not user_res.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{request.user_id}' not found."
        )

    # 2. Create DB record
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

    # 3. Enqueue job to ARQ Redis Task Queue
    try:
        redis_arq = await create_pool(RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT))
        await redis_arq.enqueue_job("process_video_render_job", str(new_job.id))
    except Exception as e:
        print(f"[ARQ Queue Warning] Could not enqueue to Redis ARQ worker: {e}. Job created in DB.")

    return VideoJobResponse(
        job_id=new_job.id,
        status=new_job.status,
        progress_percent=new_job.progress_percent,
        message="Video render task enqueued to Redis background queue."
    )


@router.get("/jobs/{job_id}", response_model=VideoJobStatusResponse, summary="Poll video job status & presigned S3 URL")
async def get_job_status(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves status, progress percent, error message, and pre-signed S3 download URL when job is COMPLETED.
    """
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
        download_url = await s3_service.generate_presigned_url(s3_key=s3_key, expiration_seconds=3600)

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
