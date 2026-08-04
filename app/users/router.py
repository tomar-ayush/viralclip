from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.db import get_async_session
from app.common.security import (
    encrypt_api_key,
    generate_key_fingerprint,
)
from app.users.model import User, UserAPIKey
from app.users.schema import (
    UserAPIKeyCreate,
    UserAPIKeyResponse,
    UserCreate,
    UserResponse,
)

router = APIRouter(prefix="/user", tags=["Users & BYOK Security"])


@router.post(
    "/create",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new platform user",
)
async def create_user(
    request: UserCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Creates a new user record in the database.
    """
    stmt = select(User).where(User.email == request.email)
    res = await session.exec(stmt)
    existing_user = res.first()
    if existing_user:
        return existing_user

    new_user = User(email=request.email)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.post(
    "/keys",
    response_model=UserAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Encrypt & store third-party BYOK API key",
)
async def store_user_api_key(
    request: UserAPIKeyCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Encrypts a user's API Key using AES-256-GCM before saving to DB.
    """
    user_stmt = select(User).where(User.id == request.user_id)
    user_res = await session.exec(user_stmt)
    if not user_res.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.user_id}' not found.",
        )

    encrypted_key = encrypt_api_key(request.api_key)
    fingerprint = generate_key_fingerprint(request.api_key)

    existing_key_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == request.user_id,
        UserAPIKey.provider == request.provider,
    )
    existing_res = await session.exec(existing_key_stmt)
    existing_key_obj = existing_res.first()

    if existing_key_obj:
        existing_key_obj.encrypted_key = encrypted_key
        existing_key_obj.key_fingerprint = fingerprint
        session.add(existing_key_obj)
        await session.commit()
        await session.refresh(existing_key_obj)
        return existing_key_obj

    new_key = UserAPIKey(
        user_id=request.user_id,
        provider=request.provider,
        encrypted_key=encrypted_key,
        key_fingerprint=fingerprint,
    )
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)
    return new_key
