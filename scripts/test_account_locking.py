"""Test script to verify account locking functionality.

This script:
1. Creates a test user
2. Simulates 3 failed login attempts
3. Verifies the account is locked
4. Tests that locked account cannot login
5. Tests auto-unlock after 30 minutes (simulated)
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User

def test_account_locking():
    """Test account locking after 3 failed attempts."""
    with app.app_context():
        # Clean up test user if exists
        test_user = User.query.filter_by(username='TEST_LOCK').first()
        if test_user:
            db.session.delete(test_user)
            db.session.commit()
        
        # Create test user
        user = User(
            username='TEST_LOCK',
            name='Test Lock User',
            is_faculty=False
        )
        user.set_password('correct_password')
        db.session.add(user)
        db.session.commit()
        print("✓ Created test user: TEST_LOCK")
        
        # Test 1: Verify initial state
        assert user.failed_login_attempts == 0
        assert user.account_locked is False
        assert user.locked_at is None
        print("✓ Initial state correct")
        
        # Test 2: First failed attempt
        user.record_failed_login()
        assert user.failed_login_attempts == 1
        assert user.account_locked is False
        print("✓ First failed attempt recorded (1/3)")
        
        # Test 3: Second failed attempt
        user.record_failed_login()
        assert user.failed_login_attempts == 2
        assert user.account_locked is False
        print("✓ Second failed attempt recorded (2/3)")
        
        # Test 4: Third failed attempt - should lock
        user.record_failed_login()
        assert user.failed_login_attempts == 3
        assert user.account_locked is True
        assert user.locked_at is not None
        print("✓ Third failed attempt - account locked!")
        
        # Test 5: Verify account is locked
        assert user.is_locked() is True
        print("✓ Account lock verified")
        
        # Test 6: Successful password check should still work but can't login
        assert user.check_password('correct_password') is True
        print("✓ Password check still works (but account is locked)")
        
        # Test 7: Test unlock
        user.unlock_account()
        assert user.account_locked is False
        assert user.failed_login_attempts == 0
        assert user.locked_at is None
        print("✓ Manual unlock successful")
        
        # Test 8: Test auto-unlock after 30 minutes
        user.record_failed_login()
        user.record_failed_login()
        user.record_failed_login()
        assert user.account_locked is True
        
        # Simulate 30 minutes passing by backdating locked_at
        user.locked_at = datetime.utcnow() - timedelta(minutes=31)
        db.session.commit()
        
        # Check if auto-unlocked
        assert user.is_locked() is False
        print("✓ Auto-unlock after 30 minutes works")
        
        # Test 9: Test successful login resets counter
        user.failed_login_attempts = 2
        db.session.commit()
        user.reset_failed_attempts()
        assert user.failed_login_attempts == 0
        print("✓ Successful login resets failed attempts")
        
        # Cleanup
        db.session.delete(user)
        db.session.commit()
        print("✓ Test user cleaned up")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nAccount locking implementation verified:")
        print("  • Locks after 3 failed attempts")
        print("  • Auto-unlocks after 30 minutes")
        print("  • Can be manually unlocked")
        print("  • Successful login resets counter")

if __name__ == '__main__':
    print("=" * 60)
    print("Account Locking Functionality Test")
    print("=" * 60)
    print()
    
    try:
        test_account_locking()
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
