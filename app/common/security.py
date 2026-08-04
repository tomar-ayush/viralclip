import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.common.config import settings


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
    """
    Encrypts a third-party BYOK API key using AES-256-GCM.
    Returns base64 encoded string containing (12-byte IV + ciphertext with tag).
    """
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
    """
    Decrypts an AES-256-GCM encrypted API key payload.
    """
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
    """
    Generates a secure, non-reversible fingerprint (SHA-256 preview)
    for UI display and duplicate checks. Example: 'sk-...4a8f'
    """
    sha = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    prefix = api_key[:4] if len(api_key) >= 4 else "key"
    suffix = sha[:8]
    return f"{prefix}...{suffix}"
