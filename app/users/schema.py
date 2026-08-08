from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.users.model import KeyProvider


class UserRegister(BaseModel):
    email: EmailStr = Field(..., example="creator@viralcut.ai")
    password: str = Field(
        ..., min_length=6, example="SecurePassword123!"
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="creator@viralcut.ai")
    password: str = Field(..., example="SecurePassword123!")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Single key upload ──────────────────────────────────────────────────────────

class UserAPIKeyCreate(BaseModel):
    provider: KeyProvider = Field(..., example=KeyProvider.OPENAI)
    api_key: str = Field(
        ..., min_length=8, example="sk-proj-1234567890abcdef"
    )
    label: str | None = Field(
        default=None,
        max_length=100,
        example="Production OpenAI Key",
        description="Optional friendly name for this key",
    )


class UserAPIKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    provider: KeyProvider
    key_fingerprint: str
    label: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Bulk key upload ────────────────────────────────────────────────────────────

class UserAPIKeyBulkCreate(BaseModel):
    """Upload multiple API keys in one request."""
    keys: list[UserAPIKeyCreate] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of API keys to upload (max 20 at once)",
        example=[
            {"provider": "openai", "api_key": "sk-proj-abc123", "label": "OpenAI Main"},
            {"provider": "openai_sora", "api_key": "sk-sora-xyz789", "label": "Sora Key"},
            {"provider": "elevenlabs", "api_key": "el-abc123def456", "label": "ElevenLabs TTS"},
        ],
    )


class UserAPIKeyBulkResult(BaseModel):
    """Result of a single key in a bulk upload."""
    provider: KeyProvider
    label: str | None
    success: bool
    key_fingerprint: str | None = None
    error: str | None = None


class UserAPIKeyBulkResponse(BaseModel):
    """Summary response for a bulk upload operation."""
    total: int
    succeeded: int
    failed: int
    results: list[UserAPIKeyBulkResult]
