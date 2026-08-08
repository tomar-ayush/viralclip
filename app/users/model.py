import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.videos.model import VideoJob


class KeyProvider(str, Enum):
    OPENAI = "openai"
    OPENAI_SORA = "openai_sora"
    ELEVENLABS = "elevenlabs"
    SERPAPI = "serpapi"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    STABILITY = "stability"
    RUNWAY = "runway"
    REPLICATE = "replicate"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    api_keys: list["UserAPIKey"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    video_jobs: list["VideoJob"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class UserAPIKey(SQLModel, table=True):
    __tablename__ = "user_api_keys"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", index=True, nullable=False
    )
    provider: KeyProvider = Field(
        sa_column=Column(String, index=True, nullable=False)
    )
    encrypted_key: str = Field(nullable=False)
    key_fingerprint: str = Field(nullable=False)
    label: str | None = Field(
        default=None,
        max_length=100,
        description="Optional friendly name for this key, e.g. 'Production OpenAI'"
    )
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationship
    user: User | None = Relationship(back_populates="api_keys")
