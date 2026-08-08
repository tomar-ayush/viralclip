from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.scripts.schema import ScriptResponse
from app.videos.model import JobStatus


class VideoRenderRequest(BaseModel):
    script_json: ScriptResponse = Field(
        ...,
        description="The timed script object generated from /scripts/generate",
    )
    background_asset_id: str = Field(
        default="gameplay_minecraft_01", example="gameplay_minecraft_01"
    )
    voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM", example="21m00Tcm4TlvDq8ikWAM"
    )


class VideoJobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    progress_percent: int
    message: str = "Video rendering task enqueued successfully"


class VideoJobStatusResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: JobStatus
    progress_percent: int
    audio_url: str | None = None
    output_video_url: str | None = None
    download_url: str | None = Field(
        default=None,
        description="Signed temporary IDrive E2 download link when COMPLETED",
    )
    error_message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
