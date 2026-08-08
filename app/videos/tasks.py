import asyncio
import uuid
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.common.db import AsyncSessionLocal
from app.common.redis import publish_job_progress
from app.common.security import decrypt_api_key
from app.storage.service import storage_service
from app.users.model import KeyProvider, UserAPIKey
from app.videos.model import JobStatus, VideoJob
from app.videos.service import elevenlabs_service, remotion_service


async def process_video_render_job(
    ctx: dict[str, Any],
    job_id: str,
    db_session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    ARQ Background Worker Task for rendering video pipeline.
    """
    job_uuid = uuid.UUID(job_id)

    async def _run(session: AsyncSession) -> dict[str, Any]:
        statement = select(VideoJob).where(VideoJob.id == job_uuid)
        result = await session.exec(statement)
        job = result.first()

        if not job:
            return {"status": "error", "message": "Job not found"}

        try:
            job.status = JobStatus.PROCESSING
            job.progress_percent = 10
            await session.commit()
            await session.refresh(job)
            await publish_job_progress(
                job_id,
                10,
                "PROCESSING",
                "Job initialized. Fetching BYOK keys...",
            )

            # Fetch ElevenLabs API Key
            key_statement = select(UserAPIKey).where(
                UserAPIKey.user_id == job.user_id,
                UserAPIKey.provider == KeyProvider.ELEVENLABS,
            )
            key_result = await session.exec(key_statement)
            api_key_obj = key_result.first()
            elevenlabs_key = "mock_elevenlabs_key"
            if api_key_obj:
                elevenlabs_key = decrypt_api_key(
                    api_key_obj.encrypted_key
                )

            # Synthesize voiceover audio
            await publish_job_progress(
                job_id,
                25,
                "PROCESSING",
                "Synthesizing audio via ElevenLabs...",
            )
            scenes = job.script_json.get("scenes", [])
            full_text = " ".join([s.get("text", "") for s in scenes])
            voice_id = job.voice_id or "21m00Tcm4TlvDq8ikWAM"

            (
                audio_bytes,
                word_captions,
            ) = await elevenlabs_service.synthesize_speech_with_timestamps(
                text=full_text,
                voice_id=voice_id,
                elevenlabs_api_key=elevenlabs_key,
            )

            # Upload audio to IDrive E2
            await publish_job_progress(
                job_id,
                45,
                "PROCESSING",
                "Uploading synthesized audio to IDrive E2...",
            )
            audio_key = f"audio/{job_id}/voiceover.mp3"
            audio_url = await storage_service.upload_bytes(
                file_bytes=audio_bytes,
                r2_key=audio_key,
                content_type="audio/mpeg",
            )
            job.audio_url = audio_url
            await session.commit()

            # Trigger Modal serverless render
            await publish_job_progress(
                job_id,
                65,
                "PROCESSING",
                "Dispatching task to Modal serverless render...",
            )
            input_props = {
                "audioUrl": audio_url,
                "backgroundAssetId": job.background_asset_id,
                "scriptJson": job.script_json,
                "wordCaptions": [
                    caption.model_dump() for caption in word_captions
                ],
            }

            for sim in [75, 85, 95]:
                await asyncio.sleep(0.1)
                await publish_job_progress(
                    job_id,
                    sim,
                    "PROCESSING",
                    f"Compositing 9:16 vertical video frames ({sim}%)...",
                )

            (
                render_id,
                output_video_url,
            ) = await remotion_service.render_media_on_lambda(
                job_id, input_props
            )

            job.output_video_url = output_video_url
            job.progress_percent = 100
            job.status = JobStatus.COMPLETED
            await session.commit()
            await session.refresh(job)

            await publish_job_progress(
                job_id,
                100,
                "COMPLETED",
                "Video rendering completed successfully!",
            )
            return {
                "status": "success",
                "job_id": job_id,
                "output_video_url": output_video_url,
            }

        except Exception as e:
            error_msg = str(e)
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            await session.commit()
            await publish_job_progress(
                job_id,
                job.progress_percent,
                "FAILED",
                f"Job failed: {error_msg}",
            )
            return {
                "status": "failed",
                "job_id": job_id,
                "error": error_msg,
            }

    if db_session:
        return await _run(db_session)
    else:
        async with AsyncSessionLocal() as session:
            return await _run(session)
