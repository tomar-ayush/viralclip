import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.db import get_async_session
from app.common.security import (
    create_access_token,
    encrypt_api_key,
    generate_key_fingerprint,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.users.model import User, UserAPIKey
from app.users.schema import (
    TokenResponse,
    UserAPIKeyBulkCreate,
    UserAPIKeyBulkResponse,
    UserAPIKeyBulkResult,
    UserAPIKeyCreate,
    UserAPIKeyResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/user", tags=["Users & Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register_user(
    request: UserRegister,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Registers a new user by hashing their password with bcrypt.
    """
    stmt = select(User).where(User.email == request.email)
    res = await session.exec(stmt)
    if res.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    hashed_pwd = get_password_hash(request.password)
    new_user = User(email=request.email, hashed_password=hashed_pwd)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and retrieve JWT Bearer token",
)
async def login_user(
    request: UserLogin,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Authenticates email and password, returning a signed JWT Access Token.
    """
    stmt = select(User).where(User.email == request.email)
    res = await session.exec(stmt)
    user = res.first()

    if not user or not verify_password(
        request.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),  # noqa: B008
):
    """
    Returns profile information for the logged-in user.
    """
    return current_user


@router.get(
    "/keys",
    response_model=list[UserAPIKeyResponse],
    summary="List all API keys for the current user",
)
async def list_user_api_keys(
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Returns all stored API keys (without the actual key values — only fingerprints).
    """
    stmt = select(UserAPIKey).where(UserAPIKey.user_id == current_user.id)
    res = await session.exec(stmt)
    return res.all()


@router.post(
    "/keys",
    response_model=UserAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Encrypt & store a single third-party BYOK API key",
)
async def store_user_api_key(
    request: UserAPIKeyCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Encrypts a user's third-party API Key using AES-256-GCM before writing to DB.
    If a key for this provider already exists, it is updated in place.
    """
    encrypted_key = encrypt_api_key(request.api_key)
    fingerprint = generate_key_fingerprint(request.api_key)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    existing_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.provider == request.provider,
    )
    existing_res = await session.exec(existing_stmt)
    existing_key = existing_res.first()

    if existing_key:
        existing_key.encrypted_key = encrypted_key
        existing_key.key_fingerprint = fingerprint
        existing_key.label = request.label
        existing_key.updated_at = now
        session.add(existing_key)
        await session.commit()
        await session.refresh(existing_key)
        return existing_key

    new_key = UserAPIKey(
        user_id=current_user.id,
        provider=request.provider,
        encrypted_key=encrypted_key,
        key_fingerprint=fingerprint,
        label=request.label,
        is_active=True,
        updated_at=now,
    )
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)
    return new_key


@router.post(
    "/keys/bulk",
    response_model=UserAPIKeyBulkResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk upload multiple third-party API keys at once",
)
async def bulk_store_user_api_keys(
    request: UserAPIKeyBulkCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Upload up to 20 API keys in a single request.

    - Each key is encrypted with AES-256-GCM before storage.
    - If a key for a provider already exists, it is **updated** (upsert).
    - Returns a detailed report: which keys succeeded and which failed (with error reason).
    - The request **does not fail entirely** if one key has an error — partial success is supported.

    **Supported providers:** openai, openai_sora, elevenlabs, serpapi, anthropic, gemini, stability, runway, replicate
    """
    results: list[UserAPIKeyBulkResult] = []
    succeeded = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for key_item in request.keys:
        try:
            encrypted_key = encrypt_api_key(key_item.api_key)
            fingerprint = generate_key_fingerprint(key_item.api_key)

            # Check for existing key for this provider
            existing_stmt = select(UserAPIKey).where(
                UserAPIKey.user_id == current_user.id,
                UserAPIKey.provider == key_item.provider,
            )
            existing_res = await session.exec(existing_stmt)
            existing_key = existing_res.first()

            if existing_key:
                existing_key.encrypted_key = encrypted_key
                existing_key.key_fingerprint = fingerprint
                existing_key.label = key_item.label
                existing_key.updated_at = now
                session.add(existing_key)
            else:
                new_key = UserAPIKey(
                    user_id=current_user.id,
                    provider=key_item.provider,
                    encrypted_key=encrypted_key,
                    key_fingerprint=fingerprint,
                    label=key_item.label,
                    is_active=True,
                    updated_at=now,
                )
                session.add(new_key)

            results.append(
                UserAPIKeyBulkResult(
                    provider=key_item.provider,
                    label=key_item.label,
                    success=True,
                    key_fingerprint=fingerprint,
                )
            )
            succeeded += 1

        except Exception as e:  # noqa: BLE001
            results.append(
                UserAPIKeyBulkResult(
                    provider=key_item.provider,
                    label=key_item.label,
                    success=False,
                    error=str(e),
                )
            )

    # Commit all successful keys in one transaction
    await session.commit()

    return UserAPIKeyBulkResponse(
        total=len(request.keys),
        succeeded=succeeded,
        failed=len(request.keys) - succeeded,
        results=results,
    )


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
)
async def delete_user_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Permanently deletes an API key by its ID.
    Only the key owner can delete it.
    """
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format.",
        )

    stmt = select(UserAPIKey).where(
        UserAPIKey.id == key_uuid,
        UserAPIKey.user_id == current_user.id,
    )
    res = await session.exec(stmt)
    key = res.first()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    await session.delete(key)
    await session.commit()
