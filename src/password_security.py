"""Password Security Module for SAS-86: Encrypt passwords at rest.

This module provides secure password hashing and verification using bcrypt,
which is more secure than the default werkzeug PBKDF2 implementation.

Features:
- Bcrypt hashing with configurable rounds (default: 12)
- Password strength validation
- Secure password comparison with timing attack protection
- Migration support for upgrading from werkzeug hashes
"""

import re
from typing import Optional, Tuple
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    # Fallback to werkzeug if bcrypt is not available
    from werkzeug.security import generate_password_hash as werkzeug_hash
    from werkzeug.security import check_password_hash as werkzeug_check


# Password policy constants
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
BCRYPT_ROUNDS = 12  # Recommended: 12-14 for good security/performance balance


class PasswordStrengthError(ValueError):
    """Raised when a password does not meet strength requirements."""
    pass


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Validate password meets minimum strength requirements.
    
    Requirements:
    - Minimum 8 characters
    - Maximum 128 characters (bcrypt limitation)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: The plaintext password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_password_strength("Test123!")
        (True, None)
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"
    
    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;~`]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


def hash_password(password: str, validate_strength: bool = False) -> str:
    """Hash a password using bcrypt (or werkzeug as fallback).
    
    Uses bcrypt with 12 rounds by default, which provides good security
    while maintaining reasonable performance (~200-300ms per hash).
    
    Args:
        password: The plaintext password to hash
        validate_strength: If True, validate password strength before hashing
        
    Returns:
        The hashed password as a string
        
    Raises:
        PasswordStrengthError: If validate_strength=True and password is weak
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
    """
    if validate_strength:
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise PasswordStrengthError(error_msg)
    
    if BCRYPT_AVAILABLE:
        # Use bcrypt for strong password hashing
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    else:
        # Fallback to werkzeug (PBKDF2)
        return werkzeug_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.
    
    Supports both bcrypt and werkzeug (PBKDF2) hashes for backward compatibility.
    Timing-attack safe comparison.
    
    Args:
        password: The plaintext password to verify
        password_hash: The stored hash to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("MyPassword123!")
        >>> verify_password("MyPassword123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    if not password or not password_hash:
        return False
    
    try:
        # Try bcrypt first
        if BCRYPT_AVAILABLE and password_hash.startswith(('$2a$', '$2b$', '$2y$')):
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        else:
            # Try werkzeug format (PBKDF2)
            return werkzeug_check(password_hash, password)
    except (ValueError, TypeError):
        # Invalid hash format
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be upgraded.
    
    Returns True if:
    - Hash is using werkzeug (PBKDF2) instead of bcrypt
    - Bcrypt hash is using fewer rounds than configured
    
    Args:
        password_hash: The stored password hash
        
    Returns:
        True if hash should be regenerated, False otherwise
    """
    if not password_hash:
        return True
    
    # If bcrypt is available but hash is not bcrypt format, needs rehash
    if BCRYPT_AVAILABLE:
        if not password_hash.startswith(('$2a$', '$2b$', '$2y$')):
            return True
        
        # Check if bcrypt rounds are less than configured
        try:
            # Extract rounds from bcrypt hash (format: $2b$12$...)
            parts = password_hash.split('$')
            if len(parts) >= 3:
                current_rounds = int(parts[2])
                return current_rounds < BCRYPT_ROUNDS
        except (ValueError, IndexError):
            return True
    
    return False


def upgrade_password_hash(password: str, old_hash: str) -> Optional[str]:
    """Upgrade a password hash to the current security standard.
    
    Only upgrades if:
    1. Old hash is valid for the given password
    2. Hash needs upgrade (see needs_rehash)
    
    Args:
        password: The plaintext password (from successful login)
        old_hash: The current password hash
        
    Returns:
        New hash if upgrade successful, None if upgrade not needed or failed
        
    Example:
        >>> old_hash = werkzeug_hash("Password123!")
        >>> new_hash = upgrade_password_hash("Password123!", old_hash)
        >>> new_hash is not None
        True
    """
    # Verify password is correct
    if not verify_password(password, old_hash):
        return None
    
    # Check if upgrade needed
    if not needs_rehash(old_hash):
        return None
    
    # Generate new hash
    return hash_password(password, validate_strength=False)


# Backward compatibility with existing code
def generate_password_hash(password: str) -> str:
    """Wrapper for hash_password to maintain API compatibility.
    
    This function maintains compatibility with code using werkzeug's
    generate_password_hash function.
    """
    return hash_password(password, validate_strength=False)


def check_password_hash(password_hash: str, password: str) -> bool:
    """Wrapper for verify_password to maintain API compatibility.
    
    This function maintains compatibility with code using werkzeug's
    check_password_hash function.
    
    Note: Parameters are in reverse order from verify_password for
    compatibility with werkzeug.
    """
    return verify_password(password, password_hash)
