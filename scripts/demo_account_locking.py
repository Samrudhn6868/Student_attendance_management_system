"""Demo script showing account locking feature in action.

This script demonstrates:
1. How failed login attempts are tracked
2. How accounts get locked after 3 failures
3. How the auto-unlock mechanism works
4. How successful logins reset the counter
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User

def demo_account_locking():
    """Interactive demo of account locking feature."""
    with app.app_context():
        # Find or create demo user
        demo_user = User.query.filter_by(username='DEMO_USER').first()
        if not demo_user:
            demo_user = User(
                username='DEMO_USER',
                name='Demo User',
                is_faculty=False
            )
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Created demo user: DEMO_USER (password: demo123)")
        else:
            # Reset demo user state
            demo_user.unlock_account()
            print("Using existing demo user: DEMO_USER (password: demo123)")
        
        print("\n" + "=" * 70)
        print("ACCOUNT LOCKING FEATURE DEMONSTRATION")
        print("=" * 70)
        
        # Demo 1: Show initial state
        print("\n1. INITIAL STATE")
        print("-" * 70)
        print(f"   Username: {demo_user.username}")
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   Account locked: {demo_user.account_locked}")
        print(f"   Locked at: {demo_user.locked_at}")
        
        # Demo 2: First failed attempt
        print("\n2. SIMULATING FAILED LOGIN ATTEMPT #1")
        print("-" * 70)
        demo_user.record_failed_login()
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   Account locked: {demo_user.account_locked}")
        print(f"   → User sees: 'Invalid password. 2 attempts remaining'")
        
        # Demo 3: Second failed attempt
        print("\n3. SIMULATING FAILED LOGIN ATTEMPT #2")
        print("-" * 70)
        demo_user.record_failed_login()
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   Account locked: {demo_user.account_locked}")
        print(f"   → User sees: 'Invalid password. 1 attempts remaining'")
        
        # Demo 4: Third failed attempt - triggers lock
        print("\n4. SIMULATING FAILED LOGIN ATTEMPT #3")
        print("-" * 70)
        demo_user.record_failed_login()
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   Account locked: {demo_user.account_locked}")
        print(f"   Locked at: {demo_user.locked_at}")
        print(f"   → User sees: 'Account locked due to multiple failed login")
        print(f"                 attempts. Please try again after 30 minutes.'")
        
        # Demo 5: Try to login while locked
        print("\n5. ATTEMPTING TO LOGIN WHILE LOCKED")
        print("-" * 70)
        is_locked = demo_user.is_locked()
        print(f"   Is account locked: {is_locked}")
        if demo_user.locked_at:
            elapsed = datetime.utcnow() - demo_user.locked_at
            remaining = 30 - int(elapsed.total_seconds() / 60)
            print(f"   Time remaining: ~{remaining} minutes")
            print(f"   → User sees: 'Account is locked. Please try again in")
            print(f"                 {remaining} minutes.'")
        
        # Demo 6: Manual unlock
        print("\n6. MANUAL UNLOCK BY ADMINISTRATOR")
        print("-" * 70)
        demo_user.unlock_account()
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   Account locked: {demo_user.account_locked}")
        print(f"   Locked at: {demo_user.locked_at}")
        print(f"   → Account is now unlocked and can login again")
        
        # Demo 7: Failed attempts then successful login
        print("\n7. FAILED ATTEMPTS FOLLOWED BY SUCCESSFUL LOGIN")
        print("-" * 70)
        demo_user.record_failed_login()
        demo_user.record_failed_login()
        print(f"   Failed attempts before success: {demo_user.failed_login_attempts}")
        print(f"   → User enters correct password")
        demo_user.reset_failed_attempts()
        print(f"   Failed attempts after success: {demo_user.failed_login_attempts}")
        print(f"   → Counter reset! User can fail 3 more times before lock")
        
        # Demo 8: Auto-unlock simulation
        print("\n8. AUTO-UNLOCK AFTER 30 MINUTES (SIMULATED)")
        print("-" * 70)
        # Lock the account
        demo_user.record_failed_login()
        demo_user.record_failed_login()
        demo_user.record_failed_login()
        print(f"   Account locked at: {demo_user.locked_at}")
        
        # Simulate 31 minutes passing
        demo_user.locked_at = datetime.utcnow() - timedelta(minutes=31)
        db.session.commit()
        print(f"   Simulated time: 31 minutes later")
        
        # Check lock status
        is_locked = demo_user.is_locked()
        print(f"   Is account still locked: {is_locked}")
        print(f"   Failed attempts: {demo_user.failed_login_attempts}")
        print(f"   → Account automatically unlocked!")
        
        print("\n" + "=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  ✓ Failed login attempts are tracked per user")
        print("  ✓ Account locks after exactly 3 failed attempts")
        print("  ✓ Locked accounts cannot login (even with correct password)")
        print("  ✓ Accounts auto-unlock after 30 minutes")
        print("  ✓ Admins can manually unlock accounts")
        print("  ✓ Successful login resets the failed attempt counter")
        print("\nSecurity Benefits:")
        print("  • Prevents brute-force password attacks")
        print("  • Limits automated credential stuffing")
        print("  • Provides time-based protection")
        print("  • User-friendly (shows remaining attempts)")

if __name__ == '__main__':
    demo_account_locking()
