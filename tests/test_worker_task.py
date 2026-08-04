from __future__ import annotations

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.common.security import get_password_hash
from app.users.model import User
from app.videos.model import JobStatus, VideoJob
from app.videos.tasks import process_video_render_job


@pytest.mark.asyncio
async def test_process_video_render_job_worker(
    db_session: AsyncSession,
):
    # 1. Seed user in test database
    new_user = User(
        email="worker_test@viralcut.ai",
        hashed_password=get_password_hash("Pass123!"),
    )
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    # 2. Seed video job record
    script_data = {
        "hook": "Secrets of AI",
        "topic": "AI Agents",
        "tone": "engaging",
        "total_estimated_duration": 15.0,
        "scenes": [
            {
                "scene_number": 1,
                "text": "AI agents are transforming code.",
                "visual_description": "AI typing on glowing screen.",
                "duration_seconds": 5.0,
            }
        ],
    }

    job = VideoJob(
        user_id=new_user.id,
        status=JobStatus.QUEUED,
        progress_percent=0,
        script_json=script_data,
        background_asset_id="gameplay_minecraft_01",
        voice_id="21m00Tcm4TlvDq8ikWAM",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # 3. Execute worker task function passing test session
    ctx = {}
    result = await process_video_render_job(
        ctx=ctx, job_id=str(job.id), db_session=db_session
    )

    assert result["status"] == "success"
    assert result["job_id"] == str(job.id)
    assert "output_video_url" in result

    # 4. Verify updated state in database
    stmt = select(VideoJob).where(VideoJob.id == job.id)
    res = await db_session.exec(stmt)
    updated_job = res.first()
    assert updated_job is not None
    assert updated_job.status == JobStatus.COMPLETED
    assert updated_job.progress_percent == 100
    assert updated_job.output_video_url is not None
