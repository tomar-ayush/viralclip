import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Relationship, SQLModel

from app.users.model import User


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VideoJob(SQLModel, table=True):
    __tablename__ = "video_jobs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", index=True, nullable=False
    )
    status: JobStatus = Field(
        default=JobStatus.QUEUED, index=True, nullable=False
    )
    progress_percent: int = Field(default=0, nullable=False)

    script_json: dict[str, Any] = Field(
        default={},
        sa_column=Column(JSON().with_variant(JSONB, "postgresql")),
    )
    background_asset_id: str | None = Field(
        default="gameplay_minecraft_01"
    )
    voice_id: str | None = Field(default="21m00Tcm4TlvDq8ikWAM")

    audio_url: str | None = Field(default=None)
    output_video_url: str | None = Field(default=None)
    error_message: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    user: User | None = Relationship(back_populates="video_jobs")
