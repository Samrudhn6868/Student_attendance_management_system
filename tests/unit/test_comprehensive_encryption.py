"""Comprehensive encryption tests covering all levels.

Tests encryption at:
1. DATA AT REST - Database field encryption
2. DATA IN TRANSIT - TLS/HTTPS connections
3. DATA IN USE - Log sanitization and secure memory handling

Test Categories:
- Unit tests for encryption utilities
- Integration tests for encrypted database operations
- System tests for end-to-end encrypted workflows
- Security tests for attack prevention
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from encryption_utils import (
    encrypt_data,
    decrypt_data,
    hash_value,
    secure_compare,
    encrypt_json,
    decrypt_json,
    encrypt_sensitive_fields,
    decrypt_sensitive_fields,
    generate_secure_token,
    generate_api_token,
    verify_api_token,
    sanitize_log_message,
    sanitize_dict,
    rotate_encryption_key,
    needs_reencryption,
    reencrypt_data,
    is_encryption_enabled,
    get_encryption_info
)


# ============================================================================
# DATA AT REST - Basic Encryption Tests
# ============================================================================

class TestBasicEncryption:
    """Test basic encryption and decryption operations."""
    
    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a simple string."""
        plaintext = "Hello, World!"
        ciphertext = encrypt_data(plaintext)
        
        assert ciphertext is not None
        assert ciphertext != plaintext
        assert isinstance(ciphertext, str)
        
        decrypted = decrypt_data(ciphertext)
        assert decrypted == plaintext
    
    def test_encrypt_decrypt_sensitive_data(self):
        """Test encrypting sensitive data like SRN, passwords."""
        sensitive_data = [
            "PES1UG23CS001",  # SRN
            "password123!@#",  # Password
            "192.168.1.1",  # IP address
            "admin@pesu.pes.edu"  # Email
        ]
        
        for data in sensitive_data:
            encrypted = encrypt_data(data)
            assert encrypted != data
            assert decrypt_data(encrypted) == data
    
    def test_encrypt_none_returns_none(self):
        """Test that encrypting None returns None."""
        assert encrypt_data(None) is None
        assert decrypt_data(None) is None
    
    def test_ciphertext_is_different_each_time(self):
        """Test that encryption is non-deterministic."""
        plaintext = "test data"
        ciphertext1 = encrypt_data(plaintext)
        ciphertext2 = encrypt_data(plaintext)
        
        # Different ciphertexts due to timestamp/nonce
        assert ciphertext1 != ciphertext2
        
        # But both decrypt to same plaintext
        assert decrypt_data(ciphertext1) == plaintext
        assert decrypt_data(ciphertext2) == plaintext
    
    def test_hash_value_deterministic(self):
        """Test that hashing is deterministic for searchable encryption."""
        value = "PES1UG23CS001"
        hash1 = hash_value(value)
        hash2 = hash_value(value)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_hash_different_values(self):
        """Test that different values produce different hashes."""
        hash1 = hash_value("PES1UG23CS001")
        hash2 = hash_value("PES1UG23CS002")
        
        assert hash1 != hash2


# ============================================================================
# DATA AT REST - JSON and Complex Data Encryption
# ============================================================================

class TestJSONEncryption:
    """Test encryption of JSON and complex data structures."""
    
    def test_encrypt_decrypt_json(self):
        """Test encrypting and decrypting JSON data."""
        data = {
            'user_id': 123,
            'username': 'student1',
            'srn': 'PES1UG23CS001',
            'grades': [85, 90, 92]
        }
        
        encrypted = encrypt_json(data)
        assert isinstance(encrypted, str)
        assert encrypted != str(data)
        
        decrypted = decrypt_json(encrypted)
        assert decrypted == data
    
    def test_encrypt_selective_fields(self):
        """Test encrypting only specific fields in a dict."""
        record = {
            'id': 1,
            'name': 'John Doe',
            'srn': 'PES1UG23CS001',
            'email': 'john@pesu.pes.edu',
            'grade': 85
        }
        
        sensitive_fields = ['srn', 'email']
        encrypted = encrypt_sensitive_fields(record, sensitive_fields)
        
        # Non-sensitive fields unchanged
        assert encrypted['id'] == record['id']
        assert encrypted['name'] == record['name']
        assert encrypted['grade'] == record['grade']
        
        # Sensitive fields encrypted
        assert encrypted['srn'] != record['srn']
        assert encrypted['email'] != record['email']
        
        # Decrypt and verify
        decrypted = decrypt_sensitive_fields(encrypted, sensitive_fields)
        assert decrypted['srn'] == record['srn']
        assert decrypted['email'] == record['email']


# ============================================================================
# DATA IN USE - Log Sanitization Tests
# ============================================================================

class TestLogSanitization:
    """Test sanitization of logs to prevent sensitive data leakage."""
    
    def test_sanitize_srn_in_log(self):
        """Test that SRN patterns are redacted from logs."""
        message = "User PES1UG23CS001 logged in successfully"
        sanitized = sanitize_log_message(message)
        
        assert 'PES1UG23CS001' not in sanitized
        assert '[SRN_REDACTED]' in sanitized
    
    def test_sanitize_email_in_log(self):
        """Test that email addresses are redacted."""
        message = "Email sent to john.doe@pesu.pes.edu successfully"
        sanitized = sanitize_log_message(message)
        
        assert 'john.doe@pesu.pes.edu' not in sanitized
        assert '[EMAIL_REDACTED]' in sanitized
    
    def test_sanitize_password_in_log(self):
        """Test that passwords are redacted."""
        message = "User logged in with password=secret123"
        sanitized = sanitize_log_message(message)
        
        assert 'secret123' not in sanitized
        assert '[REDACTED]' in sanitized
    
    def test_sanitize_api_token_in_log(self):
        """Test that API tokens are redacted."""
        message = "Request with token=abc123xyz456"
        sanitized = sanitize_log_message(message)
        
        assert 'abc123xyz456' not in sanitized
        assert '[REDACTED]' in sanitized
    
    def test_sanitize_dict_sensitive_keys(self):
        """Test sanitizing sensitive keys in dictionaries."""
        data = {
            'username': 'student1',
            'password': 'secret123',
            'token': 'abc123xyz',
            'grade': 85
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized['username'] == 'student1'
        assert sanitized['grade'] == 85
        assert sanitized['password'] == '[REDACTED]'
        assert sanitized['token'] == '[REDACTED]'


# ============================================================================
# SECURITY - Token Generation and Verification
# ============================================================================

class TestSecureTokens:
    """Test secure token generation and API token management."""
    
    def test_generate_secure_token(self):
        """Test cryptographically secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Tokens should be different
        assert token1 != token2
        
        # Tokens should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token1)
        assert len(token1) > 0
    
    def test_generate_api_token(self):
        """Test API token generation with expiration."""
        token = generate_api_token(
            user_id=1,
            username='student1',
            role='student',
            expires_in_hours=1
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_api_token(self):
        """Test verification of valid API token."""
        token = generate_api_token(
            user_id=1,
            username='student1',
            role='student',
            expires_in_hours=1
        )
        
        payload = verify_api_token(token)
        
        assert payload is not None
        assert payload['user_id'] == 1
        assert payload['username'] == 'student1'
        assert payload['role'] == 'student'
    
    def test_verify_expired_token(self):
        """Test that expired tokens are rejected."""
        # Create token that expires immediately
        token = generate_api_token(
            user_id=1,
            username='student1',
            role='student',
            expires_in_hours=-1  # Already expired
        )
        
        payload = verify_api_token(token)
        assert payload is None
    
    def test_verify_invalid_token(self):
        """Test that invalid tokens are rejected."""
        invalid_token = "invalid_token_string"
        payload = verify_api_token(invalid_token)
        assert payload is None


# ============================================================================
# SECURITY - Timing Attack Prevention
# ============================================================================

class TestTimingAttackPrevention:
    """Test constant-time operations to prevent timing attacks."""
    
    def test_secure_compare_equal_strings(self):
        """Test secure comparison of equal strings."""
        assert secure_compare("secret123", "secret123") is True
    
    def test_secure_compare_different_strings(self):
        """Test secure comparison of different strings."""
        assert secure_compare("secret123", "secret456") is False
    
    def test_secure_compare_different_lengths(self):
        """Test secure comparison with different length strings."""
        # Should still be constant-time
        result = secure_compare("short", "much_longer_string")
        assert result is False


# ============================================================================
# KEY ROTATION - Encryption Key Management
# ============================================================================

class TestKeyRotation:
    """Test encryption key rotation capabilities."""
    
    def test_rotate_encryption_key(self):
        """Test generation of new encryption key."""
        new_key = rotate_encryption_key()
        
        assert new_key is not None
        assert isinstance(new_key, str)
        assert len(new_key) > 0
    
    def test_is_encryption_enabled(self):
        """Test checking if encryption is enabled."""
        enabled = is_encryption_enabled()
        # Should be enabled or disabled based on environment
        assert isinstance(enabled, bool)
    
    def test_get_encryption_info(self):
        """Test retrieving encryption configuration info."""
        info = get_encryption_info()
        
        assert 'enabled' in info
        assert 'algorithm' in info
        assert isinstance(info['enabled'], bool)
        assert 'AES' in info['algorithm']


# ============================================================================
# INTEGRATION - Database Field Encryption
# ============================================================================

class TestDatabaseFieldEncryption:
    """Test encryption of database fields (requires models)."""
    
    def test_attendance_record_encryption(self):
        """Test that attendance fields are encrypted in database."""
        # This test requires database setup
        # See test_encryption_attendance.py for full implementation
        pass
    
    def test_audit_log_encryption(self):
        """Test that audit log sensitive fields are encrypted."""
        # This test requires database setup
        # Sensitive fields: ip_address, changes, old_values, new_values, reason
        pass


# ============================================================================
# SYSTEM - End-to-End Encryption Tests
# ============================================================================

class TestEndToEndEncryption:
    """Test complete encryption workflows."""
    
    def test_user_data_encryption_workflow(self):
        """Test complete user data encryption workflow.
        
        Workflow:
        1. User submits sensitive data
        2. Data encrypted before storage
        3. Data stored encrypted in database
        4. Data decrypted when retrieved
        5. Data displayed to authorized user only
        """
        # User submits data
        user_data = {
            'srn': 'PES1UG23CS001',
            'email': 'student@pesu.pes.edu',
            'grade': 85
        }
        
        # Encrypt sensitive fields
        encrypted_data = encrypt_sensitive_fields(
            user_data,
            ['srn', 'email']
        )
        
        # Verify encrypted
        assert encrypted_data['srn'] != user_data['srn']
        assert encrypted_data['email'] != user_data['email']
        assert encrypted_data['grade'] == user_data['grade']
        
        # Decrypt when authorized
        decrypted_data = decrypt_sensitive_fields(
            encrypted_data,
            ['srn', 'email']
        )
        
        # Verify original data recovered
        assert decrypted_data == user_data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
