"""Credential encryption using Fernet with PBKDF2 key derivation."""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def derive_key(password: str, *, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a master password.

    Uses PBKDF2 with SHA256, 480_000 iterations.
    Returns a URL-safe base64-encoded 32-byte key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    raw = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(raw)


def encrypt(plaintext: str, key: bytes) -> str:
    """Encrypt a plaintext string, return base64 ciphertext."""
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, key: bytes) -> str:
    """Decrypt a ciphertext string back to plaintext."""
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
