from __future__ import annotations

import pytest

from app.common.security import (
    create_access_token,
    decode_access_token,
    decrypt_api_key,
    encrypt_api_key,
    generate_key_fingerprint,
    get_password_hash,
    verify_password,
)


def test_aes_256_gcm_encryption_and_decryption():
    raw_api_key = "sk-proj-test1234567890abcdef"
    encrypted_b64 = encrypt_api_key(raw_api_key)

    assert encrypted_b64 != raw_api_key
    assert len(encrypted_b64) > 20

    decrypted_key = decrypt_api_key(encrypted_b64)
    assert decrypted_key == raw_api_key


def test_key_fingerprint_generation():
    key = "sk-proj-test1234567890"
    fingerprint = generate_key_fingerprint(key)
    assert fingerprint.startswith("sk-p...")
    assert len(fingerprint) > 8


def test_bcrypt_password_hashing_and_verification():
    plain_pass = "MySecretPassword123!"
    hashed_pass = get_password_hash(plain_pass)

    assert hashed_pass != plain_pass
    assert verify_password(plain_pass, hashed_pass) is True
    assert verify_password("WrongPassword", hashed_pass) is False


def test_jwt_access_token_creation_and_decoding():
    payload = {"sub": "user_123_test_uuid"}
    token = create_access_token(data=payload)

    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user_123_test_uuid"
    assert "exp" in decoded
