from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.videos.model import JobStatus
from app.scripts.schema import ScriptResponse


class VideoRenderRequest(BaseModel):
    user_id: UUID
    script_json: ScriptResponse = Field(..., description="The timed script object generated from /scripts/generate")
    background_asset_id: str = Field(default="gameplay_minecraft_01", example="gameplay_minecraft_01")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", example="21m00Tcm4TlvDq8ikWAM")


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
    audio_url: Optional[str] = None
    output_video_url: Optional[str] = None
    download_url: Optional[str] = Field(default=None, description="Signed temporary S3 download link when COMPLETED")
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
