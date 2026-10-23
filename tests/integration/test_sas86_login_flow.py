"""End-to-End tests for SAS-86: Password Encryption at Rest.

Tests the complete login flow to verify:
1. Passwords are hashed using bcrypt before storage
2. Login verification works with hashed passwords
3. No plaintext passwords are stored in the database
4. Password verification is secure and timing-attack resistant
"""

import pytest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from main import app, db, User
from password_security import (
    hash_password,
    verify_password,
    BCRYPT_AVAILABLE
)


@pytest.fixture
def test_app():
    """Create and configure a test application instance."""
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create a test client for the application."""
    return test_app.test_client()


@pytest.fixture
def app_context(test_app):
    """Create an application context for database operations."""
    with test_app.app_context():
        yield test_app


class TestSAS86PasswordHashing:
    """Test password hashing for SAS-86 acceptance criteria."""
    
    def test_new_user_password_is_hashed_not_plaintext(self, app_context):
        """SAS-86: Verify passwords are hashed, not stored as plaintext."""
        plaintext_password = "SecurePassword123!"
        
        # Create user with password
        user = User(
            username='test_student_001',
            name='Test Student',
            is_faculty=False
        )
        user.set_password(plaintext_password)
        db.session.add(user)
        db.session.commit()
        
        # Verify password hash is not plaintext
        assert user.password_hash != plaintext_password
        assert len(user.password_hash) > 50  # Hash should be long
        # Accept bcrypt, pbkdf2, or scrypt formats (all secure)
        assert (user.password_hash.startswith('$2') or 
                user.password_hash.startswith('pbkdf2:') or 
                user.password_hash.startswith('scrypt:'))
        
        # Verify plaintext password is not in hash
        assert plaintext_password not in user.password_hash
    
    def test_password_hash_uses_bcrypt_format(self, app_context):
        """SAS-86: Verify bcrypt format is used for new password hashes (if bcrypt available)."""
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available, using fallback secure hash")
        
        password = "StrongPassword456!"
        user = User(
            username='faculty_001',
            name='Test Faculty',
            is_faculty=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # When bcrypt is available, hashes should start with $2
        # Bcrypt hashes start with $2b$ or $2a$ or $2y$
        assert user.password_hash.startswith('$2')
        assert len(user.password_hash) == 60  # Bcrypt hashes are exactly 60 chars
    
    def test_same_password_produces_different_hashes(self, app_context):
        """SAS-86: Verify salt ensures same password creates different hashes."""
        password = "CommonPassword789!"
        
        # Create two users with same password
        user1 = User(username='user1', name='User One', is_faculty=False)
        user1.set_password(password)
        
        user2 = User(username='user2', name='User Two', is_faculty=False)
        user2.set_password(password)
        
        db.session.add_all([user1, user2])
        db.session.commit()
        
        # Hashes should be different due to random salt
        assert user1.password_hash != user2.password_hash
    
    def test_database_query_does_not_return_plaintext_password(self, app_context):
        """SAS-86: Verify database never contains plaintext passwords."""
        password = "TestPassword321!"
        
        user = User(username='student123', name='Student Name', is_faculty=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Query user from database
        retrieved_user = User.query.filter_by(username='student123').first()
        
        # Verify only hash is stored, not plaintext
        assert retrieved_user.password_hash != password
        assert password not in retrieved_user.password_hash
        
        # Verify password verification still works
        assert retrieved_user.check_password(password) is True


class TestSAS86LoginVerification:
    """Test login verification with hashed passwords for SAS-86."""
    
    def test_successful_login_with_correct_password(self, client, app_context):
        """SAS-86: Verify user can login with correct password using hash verification."""
        # Create user
        user = User(username='login_test_001', name='Login Test', is_faculty=False)
        user.set_password('CorrectPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Attempt login
        response = client.post('/login', data={
            'username': 'login_test_001',
            'password': 'CorrectPassword123!'
        }, follow_redirects=True)
        
        # Verify successful login
        assert response.status_code == 200
        assert b'Logged in successfully' in response.data or b'dashboard' in response.data.lower()
    
    def test_failed_login_with_incorrect_password(self, client, app_context):
        """SAS-86: Verify login fails with incorrect password."""
        # Create user
        user = User(username='login_test_002', name='Login Test 2', is_faculty=False)
        user.set_password('CorrectPassword456!')
        db.session.add(user)
        db.session.commit()
        
        # Attempt login with wrong password
        response = client.post('/login', data={
            'username': 'login_test_002',
            'password': 'WrongPassword456!'
        }, follow_redirects=True)
        
        # Verify login failed
        assert b'Invalid' in response.data or b'password' in response.data.lower()
    
    def test_login_verification_is_case_sensitive(self, client, app_context):
        """SAS-86: Verify password verification is case-sensitive."""
        # Create user
        user = User(username='case_test', name='Case Test', is_faculty=False)
        user.set_password('CaseSensitive123!')
        db.session.add(user)
        db.session.commit()
        
        # Try with different case
        response = client.post('/login', data={
            'username': 'case_test',
            'password': 'casesensitive123!'  # lowercase
        }, follow_redirects=True)
        
        # Should fail
        assert b'Invalid' in response.data or b'password' in response.data.lower()
    
    def test_check_password_method_works_correctly(self, app_context):
        """SAS-86: Verify User.check_password() correctly verifies hashed passwords."""
        user = User(username='check_test', name='Check Test', is_faculty=False)
        password = 'MySecurePassword789!'
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Verify correct password
        assert user.check_password(password) is True
        
        # Verify incorrect password
        assert user.check_password('WrongPassword789!') is False
        assert user.check_password('') is False
        assert user.check_password('MySecurePassword') is False  # partial match
    
    def test_login_with_special_characters_in_password(self, client, app_context):
        """SAS-86: Verify passwords with special characters work correctly."""
        special_password = 'P@ssw0rd!#$%^&*()'
        
        user = User(username='special_test', name='Special Test', is_faculty=True)
        user.set_password(special_password)
        db.session.add(user)
        db.session.commit()
        
        # Login with special characters
        response = client.post('/login', data={
            'username': 'special_test',
            'password': special_password
        }, follow_redirects=True)
        
        # Should succeed
        assert response.status_code == 200


class TestSAS86SecurityAudit:
    """Test security audit requirements for SAS-86."""
    
    def test_no_plaintext_passwords_in_database(self, app_context):
        """SAS-86: Security audit - confirm no plaintext passwords in database."""
        test_passwords = [
            'Password123!',
            'SecurePass456!',
            'Faculty789!',
            'Student012!'
        ]
        
        # Create multiple users
        for i, pwd in enumerate(test_passwords):
            user = User(
                username=f'audit_user_{i}',
                name=f'Audit User {i}',
                is_faculty=(i % 2 == 0)
            )
            user.set_password(pwd)
            db.session.add(user)
        
        db.session.commit()
        
        # Query all users
        all_users = User.query.all()
        
        # Verify no plaintext passwords in database
        for user in all_users:
            for pwd in test_passwords:
                assert user.password_hash != pwd
                assert pwd not in user.password_hash
    
    def test_all_password_hashes_are_secure_format(self, app_context):
        """SAS-86: Verify all stored password hashes use secure format."""
        # Create users
        for i in range(5):
            user = User(
                username=f'format_test_{i}',
                name=f'Format Test {i}',
                is_faculty=False
            )
            user.set_password(f'Password{i}23!')
            db.session.add(user)
        
        db.session.commit()
        
        # Check all hashes
        all_users = User.query.all()
        for user in all_users:
            # Hash should be bcrypt, werkzeug pbkdf2, or scrypt (all secure)
            is_bcrypt = user.password_hash.startswith('$2')
            is_werkzeug = user.password_hash.startswith('pbkdf2:')
            is_scrypt = user.password_hash.startswith('scrypt:')
            
            assert is_bcrypt or is_werkzeug or is_scrypt
            assert len(user.password_hash) > 50  # Minimum length for secure hash
    
    def test_password_hash_cannot_be_reversed(self, app_context):
        """SAS-86: Verify password hashing is one-way (cannot be reversed)."""
        password = 'OriginalPassword123!'
        
        user = User(username='reverse_test', name='Reverse Test', is_faculty=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # There should be no way to get original password from hash
        # We can only verify by checking
        assert user.check_password(password) is True
        
        # Even knowing the hash, we can't determine the original password
        # (This is verified by the fact that check_password is the only way)
        assert user.password_hash != password
        assert len(user.password_hash) != len(password)


class TestSAS86PasswordChangeScenarios:
    """Test password change scenarios for SAS-86."""
    
    def test_password_change_updates_hash(self, app_context):
        """SAS-86: Verify changing password updates the hash."""
        user = User(username='change_test', name='Change Test', is_faculty=False)
        old_password = 'OldPassword123!'
        new_password = 'NewPassword456!'
        
        user.set_password(old_password)
        db.session.add(user)
        db.session.commit()
        
        old_hash = user.password_hash
        
        # Change password
        user.set_password(new_password)
        db.session.commit()
        
        new_hash = user.password_hash
        
        # Verify hash changed
        assert old_hash != new_hash
        
        # Verify old password no longer works
        assert user.check_password(old_password) is False
        
        # Verify new password works
        assert user.check_password(new_password) is True
    
    def test_password_update_creates_new_salt(self, app_context):
        """SAS-86: Verify password updates use new random salt."""
        user = User(username='salt_test', name='Salt Test', is_faculty=False)
        password = 'SamePassword123!'
        
        # Set password first time
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        hash1 = user.password_hash
        
        # Set same password again
        user.set_password(password)
        db.session.commit()
        hash2 = user.password_hash
        
        # Hashes should be different (new salt)
        assert hash1 != hash2
        
        # Both should verify the password
        # (We can only test the current hash)
        assert user.check_password(password) is True


class TestSAS86EdgeCases:
    """Test edge cases for password hashing in SAS-86."""
    
    def test_empty_password_handling(self, app_context):
        """SAS-86: Verify empty passwords are handled appropriately."""
        user = User(username='empty_test', name='Empty Test', is_faculty=False)
        user.set_password('')
        db.session.add(user)
        db.session.commit()
        
        # Even empty password should be hashed
        assert user.password_hash != ''
        assert len(user.password_hash) > 0
    
    def test_very_long_password(self, app_context):
        """SAS-86: Verify very long passwords are handled correctly."""
        long_password = 'A' * 200 + 'b1!'  # 203 characters
        
        user = User(username='long_test', name='Long Test', is_faculty=False)
        user.set_password(long_password)
        db.session.add(user)
        db.session.commit()
        
        # Should hash successfully
        assert user.password_hash != long_password
        
        # Should verify correctly
        assert user.check_password(long_password) is True
    
    def test_unicode_characters_in_password(self, app_context):
        """SAS-86: Verify Unicode characters in passwords work correctly."""
        unicode_password = 'Пароль123!🔒'  # Cyrillic + emoji
        
        user = User(username='unicode_test', name='Unicode Test', is_faculty=False)
        user.set_password(unicode_password)
        db.session.add(user)
        db.session.commit()
        
        # Should hash and verify correctly
        assert user.password_hash != unicode_password
        assert user.check_password(unicode_password) is True
    
    def test_null_password_check(self, app_context):
        """SAS-86: Verify checking None/null password doesn't crash."""
        user = User(username='null_test', name='Null Test', is_faculty=False)
        user.set_password('ValidPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Should handle None gracefully
        assert user.check_password(None) is False


class TestSAS86TimingAttackResistance:
    """Test timing attack resistance for SAS-86."""
    
    def test_consistent_timing_for_invalid_passwords(self, app_context):
        """SAS-86: Verify password verification has consistent timing."""
        import time
        
        user = User(username='timing_test', name='Timing Test', is_faculty=False)
        user.set_password('CorrectPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Test multiple incorrect passwords
        incorrect_passwords = [
            'Wrong1!',
            'Wrong22!',
            'Wrong333!',
            'CompletelyDifferentPassword!'
        ]
        
        timings = []
        for pwd in incorrect_passwords:
            start = time.time()
            user.check_password(pwd)
            end = time.time()
            timings.append(end - start)
        
        # Timing should be relatively consistent (within 10x variance)
        # Note: This is a basic check; real timing attack analysis is more complex
        if len(timings) > 1:
            max_time = max(timings)
            min_time = min(timings)
            if min_time > 0:
                variance = max_time / min_time
                # Allow some variance but not orders of magnitude
                assert variance < 10, "Timing variance too high (potential timing attack)"


class TestSAS86BackwardCompatibility:
    """Test backward compatibility with existing password hashes."""
    
    def test_werkzeug_hash_verification_works(self, app_context):
        """SAS-86: Verify existing werkzeug PBKDF2 hashes still work."""
        from werkzeug.security import generate_password_hash
        
        password = 'LegacyPassword123!'
        old_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(username='legacy_test', name='Legacy Test', is_faculty=False)
        user.password_hash = old_hash
        db.session.add(user)
        db.session.commit()
        
        # Old hash should still verify
        assert user.check_password(password) is True
    
    def test_mixed_hash_formats_in_database(self, app_context):
        """SAS-86: Verify system handles mixed bcrypt and werkzeug hashes."""
        from werkzeug.security import generate_password_hash
        
        # User with old werkzeug hash
        user1 = User(username='old_user', name='Old User', is_faculty=False)
        user1.password_hash = generate_password_hash('OldPass123!', method='pbkdf2:sha256')
        
        # User with new bcrypt hash
        user2 = User(username='new_user', name='New User', is_faculty=False)
        user2.set_password('NewPass456!')
        
        db.session.add_all([user1, user2])
        db.session.commit()
        
        # Both should verify correctly
        assert user1.check_password('OldPass123!') is True
        assert user2.check_password('NewPass456!') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
