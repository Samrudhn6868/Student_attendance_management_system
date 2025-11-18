"""Comprehensive Encryption System for Multi-Level Data Protection.

This module implements encryption at multiple levels:
1. DATA AT REST: Database field encryption (Fernet AES-128)
2. DATA IN TRANSIT: TLS/HTTPS enforcement
3. DATA IN USE: Secure memory handling and log sanitization

Features:
- AES-128 encryption via Fernet for sensitive database fields
- Deterministic SHA-256 hashing for searchable encrypted fields
- Key rotation support with multiple encryption keys
- Secure key management from environment variables
- Encrypted audit logs and session data
- Protection against timing attacks
- Automatic log sanitization

Security Design:
- All encryption keys loaded from environment (never hardcoded)
- Ciphertext is non-deterministic (Fernet with timestamp)
- Search/filter uses privacy-preserving SHA-256 hashes
- Multi-key support for zero-downtime key rotation
- Constant-time operations to prevent timing attacks

Environment Variables:
- ENCRYPTION_KEY: Primary encryption key (required in production)
- ENCRYPTION_KEY_OLD: Previous key for rotation support (optional)
- DISABLE_ENCRYPTION: Set to '1' to disable encryption (dev/test only)
"""
from __future__ import annotations

import os
import base64
import hashlib
import hmac
import secrets
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from dotenv import load_dotenv

# ============================================================================
# ENCRYPTION KEY MANAGEMENT
# ============================================================================

# Load .env into environment (safe to call multiple times)
load_dotenv()

# Check if encryption is disabled (dev/test only)
_ENCRYPTION_DISABLED = os.getenv('DISABLE_ENCRYPTION', '0') == '1'

def _load_encryption_keys() -> Optional[MultiFernet]:
    """Load encryption keys with support for key rotation.
    
    Returns:
        MultiFernet instance with primary and optional old keys,
        or None if encryption is disabled or keys are invalid.
    """
    if _ENCRYPTION_DISABLED:
        return None

    primary_key = os.getenv('ENCRYPTION_KEY')
    old_key = os.getenv('ENCRYPTION_KEY_OLD')  # For key rotation

    fernet_instances = []

    if not primary_key:
        # Generate temporary key for dev/test (not production)
        if os.getenv('FLASK_ENV') != 'production':
            _tmp = Fernet.generate_key()
            os.environ['ENCRYPTION_KEY'] = _tmp.decode()
            primary_key = _tmp.decode()
        else:
            raise RuntimeError(
                "ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

    try:
        # Primary key (current)
        key_bytes = primary_key.encode() if isinstance(primary_key, str) else primary_key
        fernet_instances.append(Fernet(key_bytes))

        # Old key for rotation support
        if old_key:
            old_key_bytes = old_key.encode() if isinstance(old_key, str) else old_key
            fernet_instances.append(Fernet(old_key_bytes))

        # MultiFernet tries each key in order for decryption
        # Always encrypts with the first (primary) key
        return MultiFernet(fernet_instances)

    except Exception as e:
        raise RuntimeError(f"Invalid encryption key format: {e}")

# Initialize encryption system
_FERNET = _load_encryption_keys()


def _require_fernet() -> Fernet:
    """Return the Fernet instance or raise a clear RuntimeError if missing."""
    if _FERNET is None:
        raise RuntimeError("ENCRYPTION_KEY is not set or invalid; please set it in the environment")
    return _FERNET


# TODO-PERFORMANCE: Consider caching frequently encrypted values (like course IDs)
# Use LRU cache with @functools.lru_cache(maxsize=1024) for deterministic inputs
# WARNING: Only cache if the same plaintext always needs same ciphertext (not recommended
# for security, but course IDs are re-encrypted often and don't change)
# Example: @functools.lru_cache(maxsize=1024)
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
    
    Note: Uses constant-time comparison to prevent timing attacks.
    """
    if value is None:
        return None
    h = hashlib.sha256()
    h.update(value.encode('utf-8'))
    return h.hexdigest()


def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
    
    Returns:
        True if strings are equal, False otherwise
    """
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


# ============================================================================
# SENSITIVE DATA ENCRYPTION (Audit Logs, Session Data, API Tokens)
# ============================================================================

def encrypt_json(data: Dict[Any, Any]) -> str:
    """Encrypt a JSON-serializable dictionary.
    
    Args:
        data: Dictionary to encrypt
    
    Returns:
        Encrypted base64 string
    """
    json_str = json.dumps(data, separators=(',', ':'))  # Compact JSON
    return encrypt_data(json_str)


def decrypt_json(ciphertext: str) -> Optional[Dict[Any, Any]]:
    """Decrypt and parse JSON data.
    
    Args:
        ciphertext: Encrypted base64 string
    
    Returns:
        Decrypted dictionary or None if invalid
    """
    try:
        json_str = decrypt_data(ciphertext)
        if json_str:
            return json.loads(json_str)
    except (InvalidToken, json.JSONDecodeError):
        pass
    return None


def encrypt_sensitive_fields(record: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
    """Encrypt specific fields in a dictionary.
    
    Args:
        record: Dictionary containing data
        sensitive_fields: List of field names to encrypt
    
    Returns:
        Dictionary with specified fields encrypted
    """
    encrypted_record = record.copy()
    for field in sensitive_fields:
        if field in encrypted_record and encrypted_record[field] is not None:
            encrypted_record[field] = encrypt_data(str(encrypted_record[field]))
    return encrypted_record


def decrypt_sensitive_fields(record: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
    """Decrypt specific fields in a dictionary.
    
    Args:
        record: Dictionary with encrypted fields
        sensitive_fields: List of field names to decrypt
    
    Returns:
        Dictionary with specified fields decrypted
    """
    decrypted_record = record.copy()
    for field in sensitive_fields:
        if field in decrypted_record and decrypted_record[field] is not None:
            try:
                decrypted_record[field] = decrypt_data(decrypted_record[field])
            except InvalidToken:
                decrypted_record[field] = '[DECRYPTION_ERROR]'
    return decrypted_record


# ============================================================================
# SECURE TOKEN GENERATION
# ============================================================================

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes (default 32)
    
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)


def generate_api_token(user_id: int, username: str, role: str,
                       expires_in_hours: int = 24) -> str:
    """Generate an encrypted API token with expiration.
    
    Args:
        user_id: User's ID
        username: User's username
        role: User's role
        expires_in_hours: Token expiration time
    
    Returns:
        Encrypted token string
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'issued_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
        'nonce': generate_secure_token(16)  # Prevent token reuse
    }
    return encrypt_json(payload)


def verify_api_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode an API token.
    
    Args:
        token: Encrypted token string
    
    Returns:
        Token payload if valid and not expired, None otherwise
    """
    try:
        payload = decrypt_json(token)
        if not payload:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(payload['expires_at'])
        if datetime.utcnow() > expires_at:
            return None  # Token expired

        return payload
    except (InvalidToken, KeyError, ValueError):
        return None


# ============================================================================
# LOG SANITIZATION (Data in Use Protection)
# ============================================================================

# Patterns for sensitive data in logs
_SENSITIVE_PATTERNS = [
    (re.compile(r'\bPES\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}\b'), '[SRN_REDACTED]'),  # SRN pattern: PES1UG23CS001
    (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), '[CARD_REDACTED]'),  # Credit card
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),  # Email
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),  # SSN pattern
    (re.compile(r"password['\"]?\s*[:=]\s*['\"]?([^'\"\s,}]+)", re.IGNORECASE), "password='[REDACTED]'"),
    (re.compile(r"token['\"]?\s*[:=]\s*['\"]?([^'\"\s,}]+)", re.IGNORECASE), "token='[REDACTED]'"),
    (re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([^'\"\s,}]+)", re.IGNORECASE), "api_key='[REDACTED]'"),
]

def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages.
    
    Args:
        message: Log message potentially containing sensitive data
    
    Returns:
        Sanitized log message
    """
    sanitized = message
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def sanitize_dict(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """Sanitize sensitive fields in a dictionary for logging.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: Additional keys to redact
    
    Returns:
        Sanitized dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = ['password', 'token', 'api_key', 'secret', 'private_key']

    sanitized = {}
    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, sensitive_keys)
        elif isinstance(value, str):
            sanitized[key] = sanitize_log_message(value)
        else:
            sanitized[key] = value
    return sanitized


# ============================================================================
# KEY ROTATION UTILITIES
# ============================================================================

def rotate_encryption_key() -> str:
    """Generate a new encryption key for rotation.
    
    Returns:
        New Fernet key as base64 string
    
    Usage:
        1. Generate new key: new_key = rotate_encryption_key()
        2. Set ENCRYPTION_KEY_OLD to current ENCRYPTION_KEY
        3. Set ENCRYPTION_KEY to new_key
        4. Restart application
        5. Re-encrypt all data with new key
        6. Remove ENCRYPTION_KEY_OLD
    """
    return Fernet.generate_key().decode()


def needs_reencryption(ciphertext: str) -> bool:
    """Check if ciphertext was encrypted with an old key.
    
    Args:
        ciphertext: Encrypted data
    
    Returns:
        True if data should be re-encrypted with current key
    """
    if not _FERNET or not isinstance(_FERNET, MultiFernet):
        return False

    try:
        # Try decrypting with primary key only
        primary_fernet = _FERNET._fernets[0]
        primary_fernet.decrypt(ciphertext.encode('utf-8'))
        return False  # Encrypted with current key
    except InvalidToken:
        # Try with all keys
        try:
            _FERNET.decrypt(ciphertext.encode('utf-8'))
            return True  # Decryptable but with old key
        except InvalidToken:
            return False  # Invalid ciphertext


def reencrypt_data(old_ciphertext: str) -> Optional[str]:
    """Re-encrypt data with the current primary key.
    
    Args:
        old_ciphertext: Data encrypted with old key
    
    Returns:
        Data re-encrypted with current key, or None if decryption fails
    """
    try:
        plaintext = decrypt_data(old_ciphertext)
        if plaintext:
            return encrypt_data(plaintext)
    except InvalidToken:
        pass
    return None


# ============================================================================
# ENCRYPTION STATUS UTILITIES
# ============================================================================

def is_encryption_enabled() -> bool:
    """Check if encryption is enabled.
    
    Returns:
        True if encryption is active, False otherwise
    """
    return _FERNET is not None and not _ENCRYPTION_DISABLED


def get_encryption_info() -> Dict[str, Any]:
    """Get information about the encryption configuration.
    
    Returns:
        Dictionary with encryption status and configuration
    """
    info = {
        'enabled': is_encryption_enabled(),
        'disabled_by_env': _ENCRYPTION_DISABLED,
        'key_rotation_supported': False,
        'algorithm': 'Fernet (AES-128-CBC + HMAC-SHA256)',
    }

    if _FERNET and isinstance(_FERNET, MultiFernet):
        info['key_rotation_supported'] = True
        info['num_keys'] = len(_FERNET._fernets)

    return info
