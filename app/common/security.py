import base64
import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.config import settings
from app.common.db import get_async_session

# Password Hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme for Bearer token authorization header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/user/login"
)


# --- Password Hashing Utilities ---


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates a secure bcrypt hash of a plain text password."""
    return pwd_context.hash(password)


# --- JWT Token Utilities ---


def create_access_token(
    data: dict, expires_delta: timedelta | None = None
) -> str:
    """Generates a signed JWT Access Token containing user claim payload."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT Access Token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
):
    """
    FastAPI dependency to extract, decode, and authenticate current user from Bearer Token.
    """
    payload = decode_access_token(token)
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.users.model import User

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_uuid)
    res = await session.exec(stmt)
    user = res.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# --- AES-256-GCM Encryption Utilities for BYOK Keys ---


def _get_master_key_bytes() -> bytes:
    key_str = settings.ENCRYPTION_MASTER_KEY
    try:
        key_bytes = bytes.fromhex(key_str)
        if len(key_bytes) == 32:
            return key_bytes
    except ValueError:
        pass
    return hashlib.sha256(key_str.encode("utf-8")).digest()


def encrypt_api_key(plain_api_key: str) -> str:
    """Encrypts a third-party BYOK API key using AES-256-GCM."""
    if not plain_api_key:
        raise ValueError("API key cannot be empty")
    master_key = _get_master_key_bytes()
    aesgcm = AESGCM(master_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(
        nonce, plain_api_key.encode("utf-8"), associated_data=None
    )
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_api_key(encrypted_payload_b64: str) -> str:
    """Decrypts an AES-256-GCM encrypted API key payload."""
    if not encrypted_payload_b64:
        raise ValueError("Encrypted payload cannot be empty")
    master_key = _get_master_key_bytes()
    aesgcm = AESGCM(master_key)
    payload = base64.b64decode(encrypted_payload_b64.encode("utf-8"))
    if len(payload) < 13:
        raise ValueError("Invalid encrypted payload length")
    nonce = payload[:12]
    ciphertext = payload[12:]
    decrypted_bytes = aesgcm.decrypt(
        nonce, ciphertext, associated_data=None
    )
    return decrypted_bytes.decode("utf-8")


def generate_key_fingerprint(api_key: str) -> str:
    """Generates a secure, non-reversible fingerprint (SHA-256 preview) for UI display."""
    sha = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    prefix = api_key[:4] if len(api_key) >= 4 else "key"
    suffix = sha[:8]
    return f"{prefix}...{suffix}"
