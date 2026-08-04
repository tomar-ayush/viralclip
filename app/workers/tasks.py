import asyncio
import uuid
from typing import Dict, Any
from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.core.security import decrypt_api_key
from app.core.redis import publish_job_progress
from app.models.video_job import VideoJob, JobStatus
from app.models.user_api_key import UserAPIKey, KeyProvider
from app.services import s3_service, elevenlabs_service, remotion_service


async def process_video_render_job(ctx: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    """
    ARQ Background Worker Task for rendering video pipeline:
    1. Fetch job & user BYOK keys from DB
    2. Emit progress updates over Redis PubSub
    3. Synthesize narration audio via ElevenLabs
    4. Save audio to AWS S3
    5. Prepare Remotion Lambda input props
    6. Invoke Remotion Lambda render task
    7. Store output video URL and update DB status
    """
    job_uuid = uuid.UUID(job_id)

    async with AsyncSessionLocal() as session:
        # 1. Fetch job metadata
        statement = select(VideoJob).where(VideoJob.id == job_uuid)
        result = await session.exec(statement)
        job = result.first()

        if not job:
            print(f"[Worker Error] Job {job_id} not found in database.")
            return {"status": "error", "message": "Job not found"}

        try:
            # Update status to PROCESSING
            job.status = JobStatus.PROCESSING
            job.progress_percent = 10
            await session.commit()
            await session.refresh(job)
            await publish_job_progress(job_id, 10, "PROCESSING", "Job initialized. Fetching API keys...")

            # 2. Retrieve user's decrypted ElevenLabs API key
            key_statement = select(UserAPIKey).where(
                UserAPIKey.user_id == job.user_id,
                UserAPIKey.provider == KeyProvider.ELEVENLABS
            )
            key_result = await session.exec(key_statement)
            api_key_obj = key_result.first()

            elevenlabs_key = "mock_elevenlabs_key"
            if api_key_obj:
                elevenlabs_key = decrypt_api_key(api_key_obj.encrypted_key)

            # 3. Synthesize Audio
            await publish_job_progress(job_id, 25, "PROCESSING", "Synthesizing voiceover audio with ElevenLabs...")
            
            scenes = job.script_json.get("scenes", [])
            full_script_text = " ".join([s.get("text", "") for s in scenes])

            voice_id = job.voice_id or "21m00Tcm4TlvDq8ikWAM"
            audio_bytes, word_captions = await elevenlabs_service.synthesize_speech_with_timestamps(
                text=full_script_text,
                voice_id=voice_id,
                elevenlabs_api_key=elevenlabs_key
            )

            # 4. Upload Audio to S3
            await publish_job_progress(job_id, 45, "PROCESSING", "Uploading synthesized audio to S3 storage...")
            s3_audio_key = f"audio/{job_id}/voiceover.mp3"
            audio_url = await s3_service.upload_bytes(
                file_bytes=audio_bytes,
                s3_key=s3_audio_key,
                content_type="audio/mpeg"
            )

            job.audio_url = audio_url
            await session.commit()

            # 5. Format Remotion Input Props
            await publish_job_progress(job_id, 65, "PROCESSING", "Triggering AWS Remotion Lambda renderer...")
            
            input_props = {
                "audioUrl": audio_url,
                "backgroundAssetId": job.background_asset_id,
                "scriptJson": job.script_json,
                "wordCaptions": [caption.model_dump() for caption in word_captions]
            }

            # Simulated progressive progress steps during rendering
            for sim_progress in [75, 85, 95]:
                await asyncio.sleep(1.0)
                await publish_job_progress(job_id, sim_progress, "PROCESSING", f"Encoding vertical 9:16 video frame layers ({sim_progress}%)...")

            # 6. Invoke Remotion Lambda Render
            render_id, output_video_url = await remotion_service.render_media_on_lambda(job_id, input_props)

            # 7. Update final status in DB
            job.output_video_url = output_video_url
            job.progress_percent = 100
            job.status = JobStatus.COMPLETED
            await session.commit()
            await session.refresh(job)

            await publish_job_progress(job_id, 100, "COMPLETED", "Video generation complete! Ready for download.")
            
            return {
                "status": "success",
                "job_id": job_id,
                "output_video_url": output_video_url
            }

        except Exception as e:
            error_msg = str(e)
            print(f"[Worker Exception] Job {job_id} failed: {error_msg}")
            job.status = JobStatus.FAILED
            job.error_message = error_msg
            await session.commit()
            await publish_job_progress(job_id, job.progress_percent, "FAILED", f"Job failed: {error_msg}")
            return {"status": "failed", "job_id": job_id, "error": error_msg}
