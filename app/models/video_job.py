from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from app.models.user import User


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoJob(SQLModel, table=True):
    __tablename__ = "video_jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    status: JobStatus = Field(default=JobStatus.QUEUED, index=True, nullable=False)
    progress_percent: int = Field(default=0, nullable=False)
    
    # Script payload (Hook, scenes, visual cues, captions) stored as JSON/JSONB
    script_json: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    
    background_asset_id: Optional[str] = Field(default="gameplay_minecraft_01")
    voice_id: Optional[str] = Field(default="21m00Tcm4TlvDq8ikWAM") # ElevenLabs Rachel voice
    
    audio_url: Optional[str] = Field(default=None)
    output_video_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    user: Optional["User"] = Relationship(back_populates="video_jobs")
