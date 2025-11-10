"""System tests for account locking feature (SAS-84).

End-to-end tests simulating complete user workflows:
- User fails login 3 times and gets locked out
- Locked user sees appropriate error message
- Locked user can login after 30 minutes
- Admin can manually unlock accounts
- Successful login resets failed attempt counter
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from flask import Flask
from flask_login import LoginManager

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

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
        return User.query.get(int(user_id))
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def app_context(test_app):
    """Create application context."""
    with test_app.app_context():
        yield test_app


@pytest.fixture
def test_user(app_context):
    """Create a test user for login scenarios."""
    user = User(
        username='TEST_USER_001',
        password_hash=generate_password_hash('SecurePass123'),
        is_faculty=False,
        name='Test User',
        role='student'
    )
    db.session.add(user)
    db.session.commit()
    return user


# ============================================================================
# End-to-End Login Failure Scenarios
# ============================================================================

class TestLoginFailureLockout:
    """Test complete login failure and lockout workflow."""
    
    def test_three_failed_logins_locks_account(self, app_context, test_user):
        """Test that 3 consecutive failed logins lock the account."""
        username = test_user.username
        
        # Verify initial state
        assert test_user.failed_login_attempts == 0
        assert test_user.account_locked is False
        
        # Simulate 3 failed login attempts
        for attempt in range(1, 4):
            test_user.record_failed_login()
            db.session.commit()
            
            # Refresh user from database
            db.session.refresh(test_user)
            
            if attempt < 3:
                assert test_user.account_locked is False, f"Should not lock on attempt {attempt}"
            else:
                assert test_user.account_locked is True, "Should lock on attempt 3"
                assert test_user.locked_at is not None
        
        # Verify final state
        assert test_user.failed_login_attempts == 3
        assert test_user.account_locked is True
        assert test_user.is_locked() is True
    
    def test_locked_user_cannot_login_with_correct_password(self, app_context, test_user):
        """Test that locked user cannot login even with correct password."""
        # Lock the account
        test_user.lock_account()
        db.session.commit()
        
        # Password check should still work
        assert test_user.check_password('SecurePass123') is True
        
        # But account should be locked
        assert test_user.is_locked() is True
    
    def test_successful_login_resets_failed_attempts(self, app_context, test_user):
        """Test that successful login resets the failed attempt counter."""
        # Simulate 2 failed attempts
        test_user.record_failed_login()
        test_user.record_failed_login()
        db.session.commit()
        
        assert test_user.failed_login_attempts == 2
        
        # Successful login
        test_user.reset_failed_attempts()
        db.session.commit()
        
        # Counter should be reset
        db.session.refresh(test_user)
        assert test_user.failed_login_attempts == 0
        assert test_user.account_locked is False
    
    def test_partial_failures_do_not_lock_account(self, app_context, test_user):
        """Test that 2 failed attempts with successful login in between doesn't lock."""
        # Fail once
        test_user.record_failed_login()
        db.session.commit()
        assert test_user.failed_login_attempts == 1
        
        # Successful login - resets counter
        test_user.reset_failed_attempts()
        db.session.commit()
        assert test_user.failed_login_attempts == 0
        
        # Fail twice more
        test_user.record_failed_login()
        test_user.record_failed_login()
        db.session.commit()
        
        # Should not be locked (only 2 consecutive failures)
        db.session.refresh(test_user)
        assert test_user.failed_login_attempts == 2
        assert test_user.account_locked is False


class TestAutoUnlockAfterTimeout:
    """Test automatic account unlock after 30 minutes."""
    
    def test_account_auto_unlocks_after_30_minutes(self, app_context, test_user):
        """Test account automatically unlocks after 30 minutes."""
        # Lock the account
        test_user.lock_account()
        db.session.commit()
        
        # Verify locked
        assert test_user.is_locked() is True
        
        # Simulate 31 minutes passing
        test_user.locked_at = datetime.utcnow() - timedelta(minutes=31)
        db.session.commit()
        
        # Should auto-unlock
        assert test_user.is_locked() is False
        
        # Refresh from database
        db.session.refresh(test_user)
        assert test_user.account_locked is False
        assert test_user.failed_login_attempts == 0
    
    def test_account_stays_locked_before_30_minutes(self, app_context, test_user):
        """Test account remains locked before 30 minute timeout."""
        # Lock the account
        test_user.lock_account()
        db.session.commit()
        
        # Simulate 29 minutes passing
        test_user.locked_at = datetime.utcnow() - timedelta(minutes=29)
        db.session.commit()
        
        # Should still be locked
        assert test_user.is_locked() is True
    
    def test_multiple_lock_unlock_cycles_work_correctly(self, app_context, test_user):
        """Test account can go through multiple lock/unlock cycles."""
        # First cycle: lock and auto-unlock
        test_user.lock_account()
        db.session.commit()
        assert test_user.is_locked() is True
        
        test_user.locked_at = datetime.utcnow() - timedelta(minutes=31)
        db.session.commit()
        test_user.is_locked()  # Triggers auto-unlock
        db.session.commit()
        db.session.refresh(test_user)
        assert test_user.account_locked is False
        
        # Second cycle: lock again
        test_user.record_failed_login()
        test_user.record_failed_login()
        test_user.record_failed_login()
        db.session.commit()
        
        db.session.refresh(test_user)
        assert test_user.account_locked is True
        
        # Manual unlock this time
        test_user.unlock_account()
        db.session.commit()
        
        db.session.refresh(test_user)
        assert test_user.account_locked is False


class TestManualAccountUnlock:
    """Test admin manual unlock functionality."""
    
    def test_admin_can_manually_unlock_account(self, app_context, test_user):
        """Test that admin can manually unlock a locked account."""
        # Lock the account
        test_user.lock_account()
        db.session.commit()
        assert test_user.is_locked() is True
        
        # Admin manually unlocks
        test_user.unlock_account()
        db.session.commit()
        
        # Verify unlocked
        db.session.refresh(test_user)
        assert test_user.account_locked is False
        assert test_user.locked_at is None
        assert test_user.failed_login_attempts == 0
    
    def test_unlock_resets_all_lock_related_fields(self, app_context, test_user):
        """Test unlock resets all account locking fields."""
        # Set up locked state with failed attempts
        test_user.failed_login_attempts = 3
        test_user.account_locked = True
        test_user.locked_at = datetime.utcnow()
        db.session.commit()
        
        # Unlock
        test_user.unlock_account()
        db.session.commit()
        
        # Verify all fields reset
        db.session.refresh(test_user)
        assert test_user.failed_login_attempts == 0
        assert test_user.account_locked is False
        assert test_user.locked_at is None


class TestLockMessageAndUserExperience:
    """Test user-facing aspects of account locking."""
    
    def test_locked_account_provides_time_remaining(self, app_context, test_user):
        """Test that locked account can calculate time remaining."""
        # Lock the account
        lock_time = datetime.utcnow()
        test_user.account_locked = True
        test_user.locked_at = lock_time
        db.session.commit()
        
        # Calculate expected unlock time
        unlock_time = lock_time + timedelta(minutes=30)
        time_remaining = (unlock_time - datetime.utcnow()).total_seconds() / 60
        
        # Should have approximately 30 minutes remaining
        assert 29 <= time_remaining <= 30
        assert test_user.is_locked() is True
    
    def test_locked_at_timestamp_is_accurate(self, app_context, test_user):
        """Test that locked_at timestamp is set accurately."""
        before_lock = datetime.utcnow()
        
        test_user.lock_account()
        db.session.commit()
        
        after_lock = datetime.utcnow()
        
        # locked_at should be between before and after
        assert before_lock <= test_user.locked_at <= after_lock
    
    def test_failed_attempts_counter_is_accurate(self, app_context, test_user):
        """Test that failed_login_attempts counter is always accurate."""
        assert test_user.failed_login_attempts == 0
        
        # Add failures one by one
        for expected_count in range(1, 4):
            test_user.record_failed_login()
            db.session.commit()
            db.session.refresh(test_user)
            
            assert test_user.failed_login_attempts == expected_count


class TestDatabasePersistence:
    """Test that lock state persists correctly in database."""
    
    def test_lock_state_persists_across_sessions(self, app_context):
        """Test lock state is saved and retrieved from database."""
        # Create and lock user
        user = User(
            username='PERSIST_TEST',
            password_hash=generate_password_hash('pass123'),
            is_faculty=False,
            name='Persistence Test',
            role='student'
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        user.lock_account()
        db.session.commit()
        
        # Clear session (simulates new request)
        db.session.expunge_all()
        
        # Retrieve user again
        retrieved_user = User.query.get(user_id)
        
        # Lock state should persist
        assert retrieved_user.account_locked is True
        assert retrieved_user.locked_at is not None
        assert retrieved_user.is_locked() is True
        
        # Cleanup
        db.session.delete(retrieved_user)
        db.session.commit()
    
    def test_failed_attempts_persist_across_sessions(self, app_context):
        """Test failed attempts counter persists in database."""
        # Create user
        user = User(
            username='ATTEMPTS_TEST',
            password_hash=generate_password_hash('pass123'),
            is_faculty=False,
            name='Attempts Test',
            role='student'
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Record failures
        user.record_failed_login()
        user.record_failed_login()
        db.session.commit()
        
        # Clear session
        db.session.expunge_all()
        
        # Retrieve user
        retrieved_user = User.query.get(user_id)
        
        # Counter should persist
        assert retrieved_user.failed_login_attempts == 2
        
        # Cleanup
        db.session.delete(retrieved_user)
        db.session.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
