"""Integration tests for password security with User model (SAS-86).

Tests password hashing integration with database, User model, and authentication flow.
"""

import pytest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from flask import Flask
from flask_login import LoginManager
from models import db, User
from werkzeug.security import generate_password_hash


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_context(test_app):
    """Create application context."""
    with test_app.app_context():
        yield test_app


# ============================================================================
# Integration Tests
# ============================================================================

class TestUserModelPasswordHashing:
    """Test password hashing integration with User model."""
    
    def test_user_set_password_creates_hash(self, app_context):
        """Test that set_password creates a password hash."""
        user = User(
            username='TEST001',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('TestPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Password hash should exist
        assert user.password_hash is not None
        assert len(user.password_hash) > 0
        
        # Hash should not equal plaintext
        assert user.password_hash != 'TestPassword123!'
    
    def test_user_check_password_correct(self, app_context):
        """Test that check_password verifies correct password."""
        user = User(
            username='TEST002',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('CorrectPass123!')
        db.session.add(user)
        db.session.commit()
        
        assert user.check_password('CorrectPass123!') is True
    
    def test_user_check_password_incorrect(self, app_context):
        """Test that check_password rejects incorrect password."""
        user = User(
            username='TEST003',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('CorrectPass123!')
        db.session.add(user)
        db.session.commit()
        
        assert user.check_password('WrongPassword') is False
    
    def test_password_hash_persists_in_database(self, app_context):
        """Test that password hash persists correctly in database."""
        # Create user
        user = User(
            username='TEST004',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('PersistTest123!')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Clear session
        db.session.expunge_all()
        
        # Retrieve user using SQLAlchemy 2.0 API
        retrieved_user = db.session.get(User, user_id)
        
        # Password should still verify
        assert retrieved_user.check_password('PersistTest123!') is True
        assert retrieved_user.check_password('wrong') is False
    
    def test_password_change_updates_hash(self, app_context):
        """Test that changing password updates the hash."""
        user = User(
            username='TEST005',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('OldPassword123!')
        db.session.add(user)
        db.session.commit()
        
        old_hash = user.password_hash
        
        # Change password
        user.set_password('NewPassword456!')
        db.session.commit()
        
        # Hash should be different
        assert user.password_hash != old_hash
        
        # Old password should not work
        assert user.check_password('OldPassword123!') is False
        
        # New password should work
        assert user.check_password('NewPassword456!') is True


class TestPasswordSecurityInDatabase:
    """Test that passwords are securely stored in database."""
    
    def test_plaintext_password_not_stored(self, app_context):
        """Test that plaintext password is never stored."""
        password = 'PlaintextTest123!'
        user = User(
            username='TEST006',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Password hash should not contain plaintext
        assert password not in user.password_hash
        assert password.lower() not in user.password_hash.lower()
    
    def test_multiple_users_same_password_different_hashes(self, app_context):
        """Test that same password for different users produces different hashes."""
        password = 'SharedPassword123!'
        
        user1 = User(username='USER1', name='User One', is_faculty=False, role='student')
        user1.set_password(password)
        db.session.add(user1)
        
        user2 = User(username='USER2', name='User Two', is_faculty=False, role='student')
        user2.set_password(password)
        db.session.add(user2)
        
        db.session.commit()
        
        # Hashes should be different (due to random salt)
        assert user1.password_hash != user2.password_hash
        
        # But both should verify correctly
        assert user1.check_password(password) is True
        assert user2.check_password(password) is True
    
    def test_password_hash_format_is_secure(self, app_context):
        """Test that password hash uses secure format."""
        user = User(
            username='TEST007',
            name='Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('SecureFormat123!')
        db.session.add(user)
        db.session.commit()
        
        # Hash should be bcrypt or PBKDF2 format
        # Bcrypt starts with $2a$, $2b$, $2y$
        # PBKDF2 starts with pbkdf2:
        is_bcrypt = user.password_hash.startswith(('$2a$', '$2b$', '$2y$'))
        is_pbkdf2 = user.password_hash.startswith('pbkdf2:')
        
        assert is_bcrypt or is_pbkdf2


class TestLoginAuthenticationSecurity:
    """Test authentication flow with secure password handling."""
    
    def test_successful_login_with_correct_password(self, app_context):
        """Test that user can login with correct password."""
        user = User(
            username='LOGIN001',
            name='Login Test User',
            is_faculty=True,
            role='teacher'
        )
        user.set_password('LoginPass123!')
        db.session.add(user)
        db.session.commit()
        
        # Retrieve user and verify password
        retrieved_user = User.query.filter_by(username='LOGIN001').first()
        assert retrieved_user is not None
        assert retrieved_user.check_password('LoginPass123!') is True
    
    def test_failed_login_with_incorrect_password(self, app_context):
        """Test that user cannot login with incorrect password."""
        user = User(
            username='LOGIN002',
            name='Login Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('CorrectPass123!')
        db.session.add(user)
        db.session.commit()
        
        # Try incorrect password
        retrieved_user = User.query.filter_by(username='LOGIN002').first()
        assert retrieved_user.check_password('WrongPass123!') is False
    
    def test_case_sensitive_password_verification(self, app_context):
        """Test that password verification is case-sensitive."""
        user = User(
            username='LOGIN003',
            name='Login Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password('CaseSensitive123!')
        db.session.add(user)
        db.session.commit()
        
        assert user.check_password('CaseSensitive123!') is True
        assert user.check_password('casesensitive123!') is False
        assert user.check_password('CASESENSITIVE123!') is False
    
    def test_special_characters_in_password(self, app_context):
        """Test that special characters in passwords work correctly."""
        special_password = 'P@$$w0rd!#$%^&*()'
        user = User(
            username='LOGIN004',
            name='Login Test User',
            is_faculty=False,
            role='student'
        )
        user.set_password(special_password)
        db.session.add(user)
        db.session.commit()
        
        assert user.check_password(special_password) is True


class TestPasswordMigrationScenarios:
    """Test password migration and upgrade scenarios."""
    
    def test_user_with_werkzeug_hash_can_login(self, app_context):
        """Test that existing users with werkzeug hashes can still login."""
        password = 'OldUserPass123!'
        werkzeug_hash = generate_password_hash(password)
        
        # Create user with werkzeug hash directly
        user = User(
            username='MIGRATE001',
            name='Migration Test User',
            is_faculty=False,
            role='student',
            password_hash=werkzeug_hash
        )
        db.session.add(user)
        db.session.commit()
        
        # Should still verify correctly
        assert user.check_password(password) is True
    
    def test_password_rehash_on_login(self, app_context):
        """Test that password hash can be upgraded on successful login."""
        from password_security import needs_rehash, upgrade_password_hash, BCRYPT_AVAILABLE
        
        if not BCRYPT_AVAILABLE:
            pytest.skip("bcrypt not available for upgrade test")
        
        password = 'UpgradeTest123!'
        werkzeug_hash = generate_password_hash(password)
        
        user = User(
            username='MIGRATE002',
            name='Migration Test User',
            is_faculty=False,
            role='student',
            password_hash=werkzeug_hash
        )
        db.session.add(user)
        db.session.commit()
        
        # Check if upgrade needed
        if needs_rehash(user.password_hash):
            new_hash = upgrade_password_hash(password, user.password_hash)
            if new_hash:
                user.password_hash = new_hash
                db.session.commit()
        
        # Verify new hash works
        db.session.refresh(user)
        assert user.check_password(password) is True
        
        # Hash should now be bcrypt
        assert user.password_hash.startswith(('$2a$', '$2b$', '$2y$'))


class TestPasswordSecurityAudit:
    """Test security audit capabilities."""
    
    def test_no_users_with_empty_passwords(self, app_context):
        """Test that no users have empty password hashes."""
        # Create some users
        for i in range(3):
            user = User(
                username=f'AUDIT{i:03d}',
                name=f'Audit User {i}',
                is_faculty=False,
                role='student'
            )
            user.set_password(f'TestPass{i}23!')
            db.session.add(user)
        db.session.commit()
        
        # Check all users have password hashes
        users = User.query.all()
        for user in users:
            assert user.password_hash is not None
            assert len(user.password_hash) > 0
    
    def test_all_password_hashes_are_valid_format(self, app_context):
        """Test that all stored password hashes use valid formats."""
        # Create users with different hash types
        users_data = [
            ('AUDIT100', 'ValidHash123!'),
            ('AUDIT101', 'AnotherValid456!'),
            ('AUDIT102', 'ThirdValid789!')
        ]
        
        for username, password in users_data:
            user = User(
                username=username,
                name=f'User {username}',
                is_faculty=False,
                role='student'
            )
            user.set_password(password)
            db.session.add(user)
        db.session.commit()
        
        # Verify all hashes are valid
        users = User.query.all()
        for user in users:
            # Hash should be either bcrypt or PBKDF2 format
            is_valid = (
                user.password_hash.startswith(('$2a$', '$2b$', '$2y$')) or
                user.password_hash.startswith('pbkdf2:')
            )
            assert is_valid, f"Invalid hash format for user {user.username}"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_password_handling(self, app_context):
        """Test handling of empty passwords."""
        user = User(
            username='EDGE001',
            name='Edge Case User',
            is_faculty=False,
            role='student'
        )
        user.set_password('')
        db.session.add(user)
        db.session.commit()
        
        # Empty password should not verify
        assert user.check_password('') is False
        assert user.check_password('anything') is False
    
    def test_very_long_password(self, app_context):
        """Test handling of very long passwords."""
        long_password = 'A' * 100 + 'B1!'
        user = User(
            username='EDGE002',
            name='Edge Case User',
            is_faculty=False,
            role='student'
        )
        user.set_password(long_password)
        db.session.add(user)
        db.session.commit()
        
        # Should still work
        assert user.check_password(long_password) is True
    
    def test_unicode_password(self, app_context):
        """Test handling of unicode passwords."""
        unicode_password = 'Пароль123!🔒'
        user = User(
            username='EDGE003',
            name='Edge Case User',
            is_faculty=False,
            role='student'
        )
        user.set_password(unicode_password)
        db.session.add(user)
        db.session.commit()
        
        # Should work correctly
        assert user.check_password(unicode_password) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
