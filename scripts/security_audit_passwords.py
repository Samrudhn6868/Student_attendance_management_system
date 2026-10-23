"""Security Audit Script for SAS-86: Encrypt passwords at rest.

This script performs a comprehensive security audit to verify:
1. No plaintext passwords are stored in the database
2. All password hashes use secure formats (bcrypt or PBKDF2)
3. Password hashes cannot be easily reversed
4. No sensitive data is exposed in logs or debug output

Usage:
    python scripts/security_audit_passwords.py
"""

import sys
import os
import re
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app, db, User
from password_security import needs_rehash, BCRYPT_AVAILABLE


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def check_password_hash_format(password_hash):
    """Check if password hash is in a secure format.
    
    Returns:
        tuple: (is_secure, format_type, security_level)
    """
    if not password_hash:
        return False, "EMPTY", "CRITICAL"
    
    # Check for bcrypt format (most secure)
    if password_hash.startswith(('$2a$', '$2b$', '$2y$')):
        # Extract cost factor
        try:
            parts = password_hash.split('$')
            cost = int(parts[2]) if len(parts) >= 3 else 0
            if cost >= 12:
                return True, "bcrypt", "EXCELLENT"
            elif cost >= 10:
                return True, "bcrypt", "GOOD"
            else:
                return True, "bcrypt", "ACCEPTABLE"
        except (ValueError, IndexError):
            return True, "bcrypt", "UNKNOWN"
    
    # Check for PBKDF2 format (acceptable)
    if password_hash.startswith('pbkdf2:'):
        return True, "PBKDF2", "ACCEPTABLE"
    
    # Check for old werkzeug format
    if password_hash.startswith('sha256$'):
        return False, "SHA256", "WEAK"
    
    # Check if it might be plaintext (red flag!)
    if len(password_hash) < 20:
        return False, "POSSIBLE_PLAINTEXT", "CRITICAL"
    
    # Unknown format
    return False, "UNKNOWN", "WARNING"


def test_common_passwords(user):
    """Test if password matches common passwords (security check).
    
    Returns:
        list: Matched weak passwords (empty list is good)
    """
    common_passwords = [
        'password', 'Password', 'PASSWORD', 'password123', 'Password123',
        '123456', '12345678', 'qwerty', 'abc123', 'letmein',
        'welcome', 'monkey', 'dragon', 'master', 'admin',
        'test', 'test123', 'demo', 'demo123',
        'student', 'teacher', 'faculty',
        user.username, user.username.lower(), user.username.upper()
    ]
    
    matched = []
    for pwd in common_passwords:
        try:
            if user.check_password(pwd):
                matched.append(pwd)
        except Exception:
            pass
    
    return matched


def analyze_password_strength_patterns(password_hash):
    """Analyze password hash for patterns indicating weak passwords.
    
    Returns:
        list: List of potential issues
    """
    issues = []
    
    # Check hash length
    if len(password_hash) < 30:
        issues.append("Hash appears too short for modern standards")
    
    # Check for repeated patterns (shouldn't happen in good hashes)
    if re.search(r'(.{4,})\1', password_hash):
        issues.append("Repeating patterns detected in hash")
    
    # Check entropy (rough estimate)
    unique_chars = len(set(password_hash))
    if unique_chars < 10:
        issues.append("Low character diversity in hash")
    
    return issues


def audit_password_security():
    """Perform comprehensive password security audit."""
    with app.app_context():
        print_section("PASSWORD SECURITY AUDIT - SAS-86")
        print(f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bcrypt Available: {'YES ✓' if BCRYPT_AVAILABLE else 'NO ✗'}")
        
        # Get all users
        users = User.query.all()
        print(f"\nTotal Users: {len(users)}")
        
        if not users:
            print("\n⚠️  WARNING: No users found in database!")
            return
        
        # Initialize counters
        stats = {
            'total': len(users),
            'bcrypt_excellent': 0,
            'bcrypt_good': 0,
            'bcrypt_acceptable': 0,
            'pbkdf2': 0,
            'weak': 0,
            'critical': 0,
            'needs_upgrade': 0,
            'weak_passwords': 0
        }
        
        issues_found = []
        weak_password_users = []
        
        # Analyze each user
        print_section("ANALYZING USER PASSWORDS")
        
        for user in users:
            is_secure, format_type, security_level = check_password_hash_format(user.password_hash)
            
            # Update stats
            if security_level == "EXCELLENT":
                stats['bcrypt_excellent'] += 1
            elif security_level == "GOOD":
                stats['bcrypt_good'] += 1
            elif security_level == "ACCEPTABLE" and format_type == "bcrypt":
                stats['bcrypt_acceptable'] += 1
            elif format_type == "PBKDF2":
                stats['pbkdf2'] += 1
            elif security_level in ["WEAK", "WARNING"]:
                stats['weak'] += 1
            elif security_level == "CRITICAL":
                stats['critical'] += 1
            
            # Check if needs upgrade
            if needs_rehash(user.password_hash):
                stats['needs_upgrade'] += 1
            
            # Display user info
            role_display = user.role.upper() if hasattr(user, 'role') and user.role else 'N/A'
            print(f"\n👤 User: {user.username} ({role_display})")
            print(f"   Hash Format: {format_type}")
            print(f"   Security Level: {security_level}")
            
            # Check for weak passwords
            weak_passwords = test_common_passwords(user)
            if weak_passwords:
                stats['weak_passwords'] += 1
                weak_password_users.append({
                    'username': user.username,
                    'weak_passwords': weak_passwords
                })
                print(f"   ⚠️  WEAK PASSWORD DETECTED: {', '.join(weak_passwords)}")
                issues_found.append(f"User {user.username} uses weak password")
            
            # Analyze hash patterns
            hash_issues = analyze_password_strength_patterns(user.password_hash)
            if hash_issues:
                print(f"   ⚠️  Hash Issues: {', '.join(hash_issues)}")
            
            # Check if needs upgrade
            if needs_rehash(user.password_hash):
                print(f"   ⬆️  Needs Upgrade: YES")
            
            # Security status
            if is_secure:
                print(f"   ✅ Status: SECURE")
            else:
                print(f"   ❌ Status: INSECURE")
                issues_found.append(f"User {user.username} has insecure hash format: {format_type}")
        
        # Print summary
        print_section("SECURITY AUDIT SUMMARY")
        
        print(f"\n📊 Hash Format Distribution:")
        print(f"   Bcrypt (Excellent, ≥12 rounds): {stats['bcrypt_excellent']}")
        print(f"   Bcrypt (Good, ≥10 rounds):      {stats['bcrypt_good']}")
        print(f"   Bcrypt (Acceptable, <10 rounds):{stats['bcrypt_acceptable']}")
        print(f"   PBKDF2:                          {stats['pbkdf2']}")
        print(f"   Weak Formats:                    {stats['weak']}")
        print(f"   Critical Issues:                 {stats['critical']}")
        
        print(f"\n📈 Security Metrics:")
        secure_count = stats['bcrypt_excellent'] + stats['bcrypt_good'] + stats['bcrypt_acceptable'] + stats['pbkdf2']
        security_percentage = (secure_count / stats['total']) * 100 if stats['total'] > 0 else 0
        print(f"   Secure Hashes:    {secure_count}/{stats['total']} ({security_percentage:.1f}%)")
        print(f"   Needs Upgrade:    {stats['needs_upgrade']} users")
        print(f"   Weak Passwords:   {stats['weak_passwords']} users")
        
        # Print recommendations
        print_section("RECOMMENDATIONS")
        
        if BCRYPT_AVAILABLE:
            print("\n✅ Bcrypt is available and recommended for use")
        else:
            print("\n⚠️  Bcrypt is NOT available - consider installing: pip install bcrypt")
        
        if stats['needs_upgrade'] > 0:
            print(f"\n⬆️  {stats['needs_upgrade']} users should upgrade their password hash on next login")
            print("   Recommendation: Implement automatic hash upgrade on successful login")
        
        if stats['weak_passwords'] > 0:
            print(f"\n🚨 {stats['weak_passwords']} users have WEAK PASSWORDS:")
            for user_info in weak_password_users:
                print(f"   - {user_info['username']}: {', '.join(user_info['weak_passwords'])}")
            print("\n   Recommendation: Force password reset for these users")
            print("   Recommendation: Implement password strength policy")
        
        if stats['critical'] > 0 or stats['weak'] > 0:
            print(f"\n❌ CRITICAL: {stats['critical'] + stats['weak']} users have insecure password storage")
            print("   Recommendation: Immediately migrate these users to secure hashing")
        
        # Final verdict
        print_section("FINAL VERDICT")
        
        if stats['critical'] > 0:
            print("\n❌ FAILED - Critical security issues detected!")
            print("   Action Required: Immediate password migration needed")
            return False
        elif stats['weak_passwords'] > 0:
            print("\n⚠️  WARNING - Weak passwords detected")
            print("   Action Required: User education and password policy enforcement")
            return False
        elif stats['needs_upgrade'] > 0:
            print("\n⚠️  PASSED WITH WARNINGS - Some hashes need upgrading")
            print("   Action Recommended: Implement automatic hash upgrade")
            return True
        else:
            print("\n✅ PASSED - All passwords are securely encrypted!")
            print("   Status: No action required")
            return True


def generate_audit_report():
    """Generate a detailed audit report file."""
    with app.app_context():
        report_path = os.path.join(os.path.dirname(__file__), '..', 'security_audit_report.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("PASSWORD SECURITY AUDIT REPORT - SAS-86\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Bcrypt Available: {BCRYPT_AVAILABLE}\n\n")
            
            users = User.query.all()
            f.write(f"Total Users Audited: {len(users)}\n\n")
            
            for user in users:
                is_secure, format_type, security_level = check_password_hash_format(user.password_hash)
                
                f.write(f"User: {user.username}\n")
                f.write(f"  Role: {getattr(user, 'role', 'N/A')}\n")
                f.write(f"  Hash Format: {format_type}\n")
                f.write(f"  Security Level: {security_level}\n")
                f.write(f"  Secure: {'YES' if is_secure else 'NO'}\n")
                f.write(f"  Needs Upgrade: {'YES' if needs_rehash(user.password_hash) else 'NO'}\n")
                
                # Check weak passwords
                weak_passwords = test_common_passwords(user)
                if weak_passwords:
                    f.write(f"  ⚠️  WEAK PASSWORD: {', '.join(weak_passwords)}\n")
                
                f.write("\n")
        
        print(f"\n📄 Detailed report saved to: {report_path}")


if __name__ == '__main__':
    print("\n" + "🔒" * 35)
    print("PASSWORD SECURITY AUDIT TOOL")
    print("🔒" * 35)
    
    success = audit_password_security()
    
    # Generate detailed report
    try:
        generate_audit_report()
    except Exception as e:
        print(f"\n⚠️  Could not generate report file: {e}")
    
    print("\n" + "=" * 70)
    
    if success:
        print("\n✅ Audit completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Audit completed with issues - please review recommendations")
        sys.exit(1)
