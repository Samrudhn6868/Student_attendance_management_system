"""Unit tests for account locking functionality (SAS-84).

This module tests individual User model methods related to account locking:
- is_locked() - Check if account is locked with auto-unlock logic
- lock_account() - Lock an account
- unlock_account() - Unlock an account
- record_failed_login() - Increment failed attempts and lock at 3
- reset_failed_attempts() - Reset counter on successful login
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


class TestUserAccountLockingMethods:
    """Test User model account locking methods in isolation."""
    
    def test_is_locked_returns_false_when_not_locked(self):
        """Test is_locked() returns False when account_locked is False."""
        user = Mock()
        user.account_locked = False
        user.locked_at = None
        
        # Import the actual User class to use its method
        from src.models import User
        result = User.is_locked(user)
        
        assert result is False
    
    def test_is_locked_returns_true_when_locked_recently(self):
        """Test is_locked() returns True when locked within 30 minutes."""
        user = Mock()
        user.account_locked = True
        user.locked_at = datetime.utcnow() - timedelta(minutes=10)
        
        from src.models import User
        result = User.is_locked(user)
        
        assert result is True
    
    def test_is_locked_auto_unlocks_after_30_minutes(self):
        """Test is_locked() auto-unlocks when locked_at is 30+ minutes ago."""
        user = Mock()
        user.account_locked = True
        user.locked_at = datetime.utcnow() - timedelta(minutes=31)
        user.unlock_account = Mock()
        
        from src.models import User
        result = User.is_locked(user)
        
        assert result is False
        user.unlock_account.assert_called_once()
    
    def test_is_locked_handles_none_locked_at(self):
        """Test is_locked() handles None locked_at gracefully."""
        user = Mock()
        user.account_locked = True
        user.locked_at = None
        user.unlock_account = Mock()
        
        from src.models import User
        result = User.is_locked(user)
        
        # If locked_at is None but account_locked is True, should unlock
        assert result is False
        user.unlock_account.assert_called_once()
    
    def test_lock_account_sets_fields_correctly(self):
        """Test lock_account() sets account_locked and locked_at."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.account_locked = False
        user.locked_at = None
        
        with patch('src.models.db.session.commit'):
            user.lock_account()
        
        assert user.account_locked is True
        assert user.locked_at is not None
        assert isinstance(user.locked_at, datetime)
    
    def test_unlock_account_resets_fields(self):
        """Test unlock_account() resets lock fields and failed attempts."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.account_locked = True
        user.locked_at = datetime.utcnow()
        user.failed_login_attempts = 3
        
        with patch('src.models.db.session.commit'):
            user.unlock_account()
        
        assert user.account_locked is False
        assert user.locked_at is None
        assert user.failed_login_attempts == 0
    
    def test_record_failed_login_increments_counter(self):
        """Test record_failed_login() increments failed_login_attempts."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 0
        
        with patch('src.models.db.session.commit'):
            user.record_failed_login()
        
        assert user.failed_login_attempts == 1
    
    def test_record_failed_login_locks_at_three_attempts(self):
        """Test record_failed_login() locks account at 3rd attempt."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 2
        user.lock_account = Mock()
        
        with patch('src.models.db.session.commit'):
            user.record_failed_login()
        
        assert user.failed_login_attempts == 3
        user.lock_account.assert_called_once()
    
    def test_record_failed_login_does_not_lock_before_three(self):
        """Test record_failed_login() doesn't lock before 3 attempts."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 1
        user.lock_account = Mock()
        
        with patch('src.models.db.session.commit'):
            user.record_failed_login()
        
        assert user.failed_login_attempts == 2
        user.lock_account.assert_not_called()
    
    def test_reset_failed_attempts_sets_to_zero(self):
        """Test reset_failed_attempts() resets counter to 0."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 2
        
        with patch('src.models.db.session.commit'):
            user.reset_failed_attempts()
        
        assert user.failed_login_attempts == 0
    
    def test_reset_failed_attempts_works_when_already_zero(self):
        """Test reset_failed_attempts() is safe when already 0."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 0
        
        with patch('src.models.db.session.commit'):
            user.reset_failed_attempts()
        
        assert user.failed_login_attempts == 0


class TestAccountLockingThresholds:
    """Test account locking thresholds and edge cases."""
    
    def test_exactly_three_attempts_triggers_lock(self):
        """Test that exactly 3 failed attempts triggers lock."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 0
        
        with patch('src.models.db.session.commit'):
            user.record_failed_login()  # 1
            assert user.account_locked is False
            
            user.record_failed_login()  # 2
            assert user.account_locked is False
            
            user.record_failed_login()  # 3
            assert user.account_locked is True
    
    def test_lock_timeout_is_exactly_30_minutes(self):
        """Test auto-unlock happens at exactly 30 minutes."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.account_locked = True
        
        # Test at 29 minutes, 59 seconds - should still be locked
        user.locked_at = datetime.utcnow() - timedelta(minutes=29, seconds=59)
        assert user.is_locked() is True
        
        # Test at exactly 30 minutes - should unlock
        user.account_locked = True  # Reset for next test
        user.locked_at = datetime.utcnow() - timedelta(minutes=30, seconds=1)
        
        with patch('src.models.db.session.commit'):
            result = user.is_locked()
        
        assert result is False
    
    def test_multiple_lock_unlock_cycles(self):
        """Test account can be locked and unlocked multiple times."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        
        with patch('src.models.db.session.commit'):
            # First cycle
            user.record_failed_login()
            user.record_failed_login()
            user.record_failed_login()
            assert user.account_locked is True
            
            user.unlock_account()
            assert user.account_locked is False
            
            # Second cycle
            user.record_failed_login()
            user.record_failed_login()
            user.record_failed_login()
            assert user.account_locked is True
            
            user.unlock_account()
            assert user.account_locked is False


class TestAccountLockingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_lock_account_idempotent(self):
        """Test locking an already locked account is safe."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        
        with patch('src.models.db.session.commit'):
            user.lock_account()
            first_locked_at = user.locked_at
            
            # Lock again
            user.lock_account()
            second_locked_at = user.locked_at
            
            assert user.account_locked is True
            # Should update locked_at to current time
            assert second_locked_at >= first_locked_at
    
    def test_unlock_account_idempotent(self):
        """Test unlocking an already unlocked account is safe."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.account_locked = False
        
        with patch('src.models.db.session.commit'):
            user.unlock_account()
        
        assert user.account_locked is False
        assert user.locked_at is None
        assert user.failed_login_attempts == 0
    
    def test_failed_attempts_do_not_go_negative(self):
        """Test failed_login_attempts cannot go negative."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.failed_login_attempts = 0
        
        with patch('src.models.db.session.commit'):
            user.reset_failed_attempts()
        
        assert user.failed_login_attempts == 0
    
    def test_is_locked_with_future_locked_at(self):
        """Test is_locked() handles future locked_at timestamp."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.account_locked = True
        user.locked_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Future timestamp should still be considered locked
        assert user.is_locked() is True
    
    def test_password_check_independent_of_lock_state(self):
        """Test password checking works regardless of lock state."""
        from src.models import User
        
        user = User(username='test', name='Test', is_faculty=False)
        user.set_password('test123')
        
        # Lock the account
        with patch('src.models.db.session.commit'):
            user.lock_account()
        
        # Password check should still work
        assert user.check_password('test123') is True
        assert user.check_password('wrong') is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
