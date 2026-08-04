from datetime import datetime, timezone
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user_api_key import UserAPIKey
    from app.models.video_job import VideoJob


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    api_keys: List["UserAPIKey"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    video_jobs: List["VideoJob"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
