"""Migration script to upgrade password hashes to bcrypt (SAS-86).

This script upgrades existing password hashes from werkzeug (PBKDF2) to bcrypt
for enhanced security. It cannot upgrade hashes directly as the plaintext
password is not available, but it prepares the system for upgrade-on-login.

Usage:
    python scripts/migrate_password_hashing.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User
from password_security import needs_rehash, BCRYPT_AVAILABLE


def migrate_password_hashing():
    """Prepare database for password hash migration."""
    with app.app_context():
        print("=" * 70)
        print("PASSWORD HASH MIGRATION - SAS-86")
        print("=" * 70)
        print(f"\nBcrypt Available: {'YES ✓' if BCRYPT_AVAILABLE else 'NO ✗'}\n")
        
        if not BCRYPT_AVAILABLE:
            print("⚠️  WARNING: Bcrypt is not installed!")
            print("   Install it with: pip install bcrypt")
            print("   Continuing with werkzeug (PBKDF2) hashing...")
            print()
        
        # Get all users
        users = User.query.all()
        print(f"Total Users: {len(users)}\n")
        
        if not users:
            print("⚠️  No users found in database")
            return
        
        # Analyze current state
        needs_upgrade_count = 0
        upgrade_candidates = []
        
        print("Analyzing password hashes...")
        print("-" * 70)
        
        for user in users:
            hash_format = "Unknown"
            if user.password_hash.startswith(('$2a$', '$2b$', '$2y$')):
                hash_format = "bcrypt"
            elif user.password_hash.startswith('pbkdf2:'):
                hash_format = "PBKDF2"
            elif user.password_hash.startswith('sha256$'):
                hash_format = "SHA256 (old)"
            
            needs_upgrade = needs_rehash(user.password_hash)
            
            print(f"\n👤 {user.username}")
            print(f"   Current Hash: {hash_format}")
            print(f"   Needs Upgrade: {'YES' if needs_upgrade else 'NO'}")
            
            if needs_upgrade:
                needs_upgrade_count += 1
                upgrade_candidates.append(user)
        
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"\n📊 Statistics:")
        print(f"   Total Users: {len(users)}")
        print(f"   Need Upgrade: {needs_upgrade_count}")
        print(f"   Already Secure: {len(users) - needs_upgrade_count}")
        
        if needs_upgrade_count == 0:
            print("\n✅ All password hashes are already using the latest secure format!")
            print("   No migration needed.")
            return
        
        print("\n" + "=" * 70)
        print("MIGRATION STRATEGY")
        print("=" * 70)
        
        print("\n⚠️  IMPORTANT: Password hash upgrade requires user login")
        print("\nWhy: We cannot upgrade hashes without the plaintext password,")
        print("     which is only available during login.")
        
        print("\n📋 Migration Steps:")
        print("\n1. Deploy the new password_security module")
        print("2. Update login route to upgrade hashes automatically:")
        print()
        print("   # In login route, after successful password verification:")
        print("   from password_security import needs_rehash, upgrade_password_hash")
        print()
        print("   if user.check_password(password):")
        print("       # Check if hash needs upgrade")
        print("       if needs_rehash(user.password_hash):")
        print("           new_hash = upgrade_password_hash(password, user.password_hash)")
        print("           if new_hash:")
        print("               user.password_hash = new_hash")
        print("               db.session.commit()")
        print("               print(f'Upgraded hash for {user.username}')")
        print()
        
        print("3. Notify users to login to upgrade their password security")
        print("4. Monitor upgrade progress using security_audit_passwords.py")
        
        print("\n" + "=" * 70)
        print("USERS REQUIRING UPGRADE")
        print("=" * 70)
        
        for user in upgrade_candidates:
            print(f"   - {user.username} ({getattr(user, 'role', 'N/A')})")
        
        print("\n" + "=" * 70)
        print("OPTIONAL: Force Password Reset")
        print("=" * 70)
        
        print("\nFor maximum security, you can force users to reset passwords:")
        print()
        print("   # Mark users for password reset")
        print("   for user in User.query.all():")
        print("       user.force_password_reset = True  # Add this column to User model")
        print("   db.session.commit()")
        print()
        
        print("⚠️  This is OPTIONAL and not required for SAS-86 compliance")
        
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        
        print("\n1. ✅ Update requirements.txt to include: bcrypt>=4.0.0")
        print("2. ✅ Deploy password_security module")
        print("3. ✅ Update main.py login route (see code above)")
        print("4. 📊 Run security audit: python scripts/security_audit_passwords.py")
        print("5. 📧 Notify users to login for automatic upgrade")
        print("6. ✅ Re-run audit after migration period to verify")
        
        print("\n✨ Migration preparation complete!")


def create_auto_upgrade_example():
    """Create an example login route with auto-upgrade."""
    example_code = '''
# Example: Updated login route with automatic password hash upgrade

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route with automatic password hash upgrade."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # === NEW: Auto-upgrade password hash ===
            from password_security import needs_rehash, upgrade_password_hash
            
            if needs_rehash(user.password_hash):
                new_hash = upgrade_password_hash(password, user.password_hash)
                if new_hash:
                    user.password_hash = new_hash
                    db.session.commit()
                    flash('Your password security has been upgraded.', 'info')
            # === End auto-upgrade ===
            
            # Reset failed attempts on successful login
            user.reset_failed_attempts()
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')
'''
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'login_auto_upgrade_example.py')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(example_code)
    
    print(f"\n📝 Example code saved to: {output_path}")


if __name__ == '__main__':
    print("\n" + "🔐" * 35)
    print("PASSWORD HASH MIGRATION TOOL")
    print("🔐" * 35)
    print()
    
    try:
        migrate_password_hashing()
        create_auto_upgrade_example()
        
        print("\n" + "=" * 70)
        print("✅ Migration preparation completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
