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
    session: AsyncSession = Depends(get_async_session),
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
    session: AsyncSession = Depends(get_async_session),
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
    current_user: User = Depends(get_current_user),
):
    """
    Returns profile information for the logged-in user.
    """
    return current_user


@router.post(
    "/keys",
    response_model=UserAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Encrypt & store third-party BYOK API key",
)
async def store_user_api_key(
    request: UserAPIKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Encrypts a user's third-party API Key using AES-256-GCM before writing to PostgreSQL DB.
    """
    encrypted_key = encrypt_api_key(request.api_key)
    fingerprint = generate_key_fingerprint(request.api_key)

    existing_key_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == current_user.id,
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
        user_id=current_user.id,
        provider=request.provider,
        encrypted_key=encrypted_key,
        key_fingerprint=fingerprint,
    )
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)
    return new_key
