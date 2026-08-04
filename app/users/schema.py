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


class UserAPIKeyCreate(BaseModel):
    provider: KeyProvider = Field(..., example=KeyProvider.OPENAI)
    api_key: str = Field(
        ..., min_length=8, example="sk-proj-1234567890abcdef"
    )


class UserAPIKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    provider: KeyProvider
    key_fingerprint: str
    created_at: datetime

    class Config:
        from_attributes = True
