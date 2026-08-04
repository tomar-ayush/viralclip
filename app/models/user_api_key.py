from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class KeyProvider(str, Enum):
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    SERPAPI = "serpapi"
    ANTHROPIC = "anthropic"


class UserAPIKey(SQLModel, table=True):
    __tablename__ = "user_api_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    provider: KeyProvider = Field(index=True, nullable=False)
    encrypted_key: str = Field(nullable=False)
    key_fingerprint: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    user: Optional["User"] = Relationship(back_populates="api_keys")
