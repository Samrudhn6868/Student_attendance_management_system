"""Unit tests for password security module (SAS-86).

Tests password hashing, verification, strength validation, and migration capabilities.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from password_security import (
    hash_password,
    verify_password,
    validate_password_strength,
    needs_rehash,
    upgrade_password_hash,
    generate_password_hash,
    check_password_hash,
    PasswordStrengthError,
    BCRYPT_AVAILABLE
)


class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a non-empty hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Hash should not equal plaintext
    
    def test_hash_password_different_for_same_input(self):
        """Test that same password produces different hashes (salt is random)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Due to random salt, hashes should be different
        assert hash1 != hash2
    
    def test_hash_password_with_bcrypt(self):
        """Test that bcrypt hash format is correct."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Bcrypt hashes start with $2a$, $2b$, or $2y$
        assert hashed.startswith(('$2a$', '$2b$', '$2y$'))
    
    def test_hash_password_with_strength_validation(self):
        """Test that weak passwords are rejected when validation enabled."""
        weak_password = "weak"
        
        with pytest.raises(PasswordStrengthError):
            hash_password(weak_password, validate_strength=True)
    
    def test_hash_password_accepts_strong_password(self):
        """Test that strong passwords pass validation."""
        strong_password = "StrongPass123!@#"
        
        # Should not raise exception
        hashed = hash_password(strong_password, validate_strength=True)
        assert hashed is not None


class TestPasswordVerification:
    """Test password verification functionality."""
    
    def test_verify_password_correct(self):
        """Test that correct password verifies successfully."""
        password = "CorrectPass123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test that incorrect password fails verification."""
        password = "CorrectPass123!"
        wrong_password = "WrongPass123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password("testpassword123!", hashed) is False
        assert verify_password("TESTPASSWORD123!", hashed) is False
    
    def test_verify_password_empty_inputs(self):
        """Test that empty password or hash returns False."""
        assert verify_password("", "somehash") is False
        assert verify_password("password", "") is False
        assert verify_password("", "") is False
    
    def test_verify_password_with_werkzeug_hash(self):
        """Test that verification works with werkzeug PBKDF2 hashes."""
        from werkzeug.security import generate_password_hash as werkzeug_hash
        
        password = "TestPassword123!"
        werkzeug_hashed = werkzeug_hash(password)
        
        # Should verify correctly
        assert verify_password(password, werkzeug_hashed) is True
    
    def test_verify_password_timing_attack_resistant(self):
        """Test that verification time is consistent (basic check)."""
        import time
        
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Time correct password
        start = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start
        
        # Time incorrect password
        start = time.time()
        verify_password("WrongPassword123!", hashed)
        incorrect_time = time.time() - start
        
        # Times should be similar (within 50ms)
        # Note: This is a basic check, not a comprehensive timing attack test
        time_diff = abs(correct_time - incorrect_time)
        assert time_diff < 0.05


class TestPasswordStrengthValidation:
    """Test password strength validation."""
    
    def test_validate_empty_password(self):
        """Test that empty password fails validation."""
        is_valid, error = validate_password_strength("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()
    
    def test_validate_too_short_password(self):
        """Test that short passwords fail validation."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "at least 8 characters" in error.lower()
    
    def test_validate_too_long_password(self):
        """Test that excessively long passwords fail validation."""
        long_password = "A" * 129 + "1!"
        is_valid, error = validate_password_strength(long_password)
        assert is_valid is False
        assert "must not exceed" in error.lower()
    
    def test_validate_no_uppercase(self):
        """Test that password without uppercase fails."""
        is_valid, error = validate_password_strength("password123!")
        assert is_valid is False
        assert "uppercase" in error.lower()
    
    def test_validate_no_lowercase(self):
        """Test that password without lowercase fails."""
        is_valid, error = validate_password_strength("PASSWORD123!")
        assert is_valid is False
        assert "lowercase" in error.lower()
    
    def test_validate_no_digit(self):
        """Test that password without digit fails."""
        is_valid, error = validate_password_strength("PasswordOnly!")
        assert is_valid is False
        assert "digit" in error.lower()
    
    def test_validate_no_special_character(self):
        """Test that password without special character fails."""
        is_valid, error = validate_password_strength("Password123")
        assert is_valid is False
        assert "special character" in error.lower()
    
    def test_validate_strong_password(self):
        """Test that strong password passes validation."""
        is_valid, error = validate_password_strength("StrongPass123!@#")
        assert is_valid is True
        assert error is None
    
    def test_validate_various_special_characters(self):
        """Test that various special characters are accepted."""
        special_chars = "!@#$%^&*(),.?\":{}|<>_-+=[]\\/"
        
        for char in special_chars:
            password = f"TestPass1{char}"
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Failed with special char: {char}"


class TestPasswordHashRehashing:
    """Test password hash upgrade functionality."""
    
    def test_needs_rehash_with_werkzeug_hash(self):
        """Test that werkzeug hash is flagged for rehash."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        from werkzeug.security import generate_password_hash as werkzeug_hash
        
        old_hash = werkzeug_hash("TestPassword123!")
        assert needs_rehash(old_hash) is True
    
    def test_needs_rehash_with_bcrypt_hash(self):
        """Test that bcrypt hash is not flagged for rehash."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        password = "TestPassword123!"
        bcrypt_hash = hash_password(password)
        
        # Fresh bcrypt hash should not need rehashing
        assert needs_rehash(bcrypt_hash) is False
    
    def test_needs_rehash_empty_hash(self):
        """Test that empty hash needs rehashing."""
        assert needs_rehash("") is True
        assert needs_rehash(None) is True
    
    def test_upgrade_password_hash_from_werkzeug(self):
        """Test upgrading from werkzeug to bcrypt hash."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        from werkzeug.security import generate_password_hash as werkzeug_hash
        
        password = "TestPassword123!"
        old_hash = werkzeug_hash(password)
        
        new_hash = upgrade_password_hash(password, old_hash)
        
        assert new_hash is not None
        assert new_hash != old_hash
        assert new_hash.startswith(('$2a$', '$2b$', '$2y$'))
        assert verify_password(password, new_hash) is True
    
    def test_upgrade_password_hash_wrong_password(self):
        """Test that upgrade fails with wrong password."""
        from werkzeug.security import generate_password_hash as werkzeug_hash
        
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        old_hash = werkzeug_hash(password)
        
        new_hash = upgrade_password_hash(wrong_password, old_hash)
        
        assert new_hash is None
    
    def test_upgrade_password_hash_already_upgraded(self):
        """Test that already-upgraded hash returns None."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        password = "TestPassword123!"
        bcrypt_hash = hash_password(password)
        
        result = upgrade_password_hash(password, bcrypt_hash)
        
        # Should return None as no upgrade needed
        assert result is None


class TestBackwardCompatibility:
    """Test backward compatibility with werkzeug API."""
    
    def test_generate_password_hash_compatibility(self):
        """Test that generate_password_hash works as drop-in replacement."""
        password = "TestPassword123!"
        hashed = generate_password_hash(password)
        
        assert hashed is not None
        assert len(hashed) > 0
    
    def test_check_password_hash_compatibility(self):
        """Test that check_password_hash works with reversed parameters."""
        password = "TestPassword123!"
        hashed = generate_password_hash(password)
        
        # Note: werkzeug uses (hash, password) order
        assert check_password_hash(hashed, password) is True
        assert check_password_hash(hashed, "wrong") is False
    
    def test_compatibility_with_existing_werkzeug_hashes(self):
        """Test that existing werkzeug hashes still work."""
        from werkzeug.security import generate_password_hash as werkzeug_hash
        
        password = "TestPassword123!"
        werkzeug_hashed = werkzeug_hash(password)
        
        # Should work with our check function
        assert check_password_hash(werkzeug_hashed, password) is True


class TestSecurityProperties:
    """Test security properties of password hashing."""
    
    def test_password_not_recoverable_from_hash(self):
        """Test that original password cannot be recovered from hash."""
        password = "SecretPassword123!"
        hashed = hash_password(password)
        
        # Hash should not contain the password
        assert password not in hashed
        assert password.lower() not in hashed.lower()
    
    def test_similar_passwords_have_different_hashes(self):
        """Test that similar passwords produce different hashes."""
        password1 = "TestPassword123!"
        password2 = "TestPassword124!"
        
        hash1 = hash_password(password1)
        hash2 = hash_password(password2)
        
        assert hash1 != hash2
    
    def test_hash_length_consistent(self):
        """Test that hash length is consistent."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available")
        
        password1 = "Short1!"
        password2 = "AVeryLongPasswordThatExceedsTheShortOne123!"
        
        hash1 = hash_password(password1, validate_strength=False)
        hash2 = hash_password(password2)
        
        # Bcrypt hashes should be same length (60 chars)
        assert len(hash1) == len(hash2) == 60
    
    def test_null_byte_handling(self):
        """Test that null bytes in password are handled correctly."""
        password = "Test\x00Password123!"
        
        # Should handle null bytes without crashing
        hashed = hash_password(password, validate_strength=False)
        assert verify_password(password, hashed) is True
    
    def test_unicode_password_support(self):
        """Test that unicode passwords are supported."""
        password = "Пароль123!🔒"  # Russian + emoji
        
        hashed = hash_password(password, validate_strength=False)
        assert verify_password(password, hashed) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
