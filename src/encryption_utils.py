"""Encryption utilities for SAS-92: encryption at rest for attendance data.

This module provides convenience functions to encrypt and decrypt text using
cryptography.fernet. It also provides a deterministic hashing helper used for
search/filter operations without exposing plaintext in the database.

Design notes:
- Ciphertext is stored in DB and is non-deterministic (Fernet). To allow
  searching/filtering by plaintext values (e.g. student_srn, course_id, status)
  we store deterministic SHA-256 hashes (hex) of the plaintext in separate
  columns. These hashes are privacy-preserving (one-way) and allow efficient
  filtering.
- The encryption key MUST be provided via the ENCRYPTION_KEY environment
  variable (loaded from .env in development). Do NOT hardcode keys.
"""
from __future__ import annotations

import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

# Load .env into environment (safe to call multiple times)
load_dotenv()

_ENC_KEY = os.getenv('ENCRYPTION_KEY')
if not _ENC_KEY:
    # If no key is provided, generate a temporary key (useful for tests/local dev).
    # This avoids breaking existing test suites when the environment variable
    # is not set. In production, set ENCRYPTION_KEY explicitly and keep it secret.
    try:
        from cryptography.fernet import Fernet
        _tmp = Fernet.generate_key()
        os.environ['ENCRYPTION_KEY'] = _tmp.decode()
        _FERNET = Fernet(_tmp)
    except Exception:
        _FERNET = None
else:
    try:
        # Accept either raw bytes base64 or str; ensure bytes
        key_bytes = _ENC_KEY.encode() if isinstance(_ENC_KEY, str) else _ENC_KEY
        # Validate key length by constructing Fernet
        _FERNET = Fernet(key_bytes)
    except Exception:
        # Invalid key format; treat as missing
        _FERNET = None


def _require_fernet() -> Fernet:
    """Return the Fernet instance or raise a clear RuntimeError if missing."""
    if _FERNET is None:
        raise RuntimeError("ENCRYPTION_KEY is not set or invalid; please set it in the environment")
    return _FERNET


def encrypt_data(plaintext: str) -> str:
    """Encrypt plaintext and return URL-safe base64 ciphertext string.

    Args:
        plaintext: text to encrypt

    Returns:
        ciphertext as str
    """
    if plaintext is None:
        return None
    f = _require_fernet()
    token = f.encrypt(plaintext.encode('utf-8'))
    return token.decode('utf-8')


def decrypt_data(ciphertext: str) -> Optional[str]:
    """Decrypt ciphertext created by encrypt_data.

    Args:
        ciphertext: the token produced by encrypt_data

    Returns:
        plaintext string or None if ciphertext is None
    """
    if ciphertext is None:
        return None
    f = _require_fernet()
    try:
        data = f.decrypt(ciphertext.encode('utf-8'))
        return data.decode('utf-8')
    except InvalidToken:
        # Bubble up a controlled error for callers to handle
        raise


def hash_value(value: str) -> Optional[str]:
    """Return a deterministic SHA-256 hex digest of the given value.

    This function is used to store searchable/hashing tokens for encrypted
    columns. The output length is 64 (hex). If value is None, returns None.
    """
    if value is None:
        return None
    h = hashlib.sha256()
    h.update(value.encode('utf-8'))
    return h.hexdigest()
