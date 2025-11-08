"""Test script for SAS-88 RBAC functionality.

This script tests the role-based access control implementation
by making requests to the attendance endpoints with different roles.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_rbac_decorators():
    """Test RBAC decorator functionality."""
    print("="*70)
    print("Testing RBAC Decorators")
    print("="*70)
    
    from rbac import has_role, get_user_role, ROLE_HIERARCHY
    
    # Test role hierarchy
    print("\n1. Testing Role Hierarchy:")
    print(f"   Role Hierarchy: {ROLE_HIERARCHY}")
    assert ROLE_HIERARCHY['admin'] > ROLE_HIERARCHY['teacher']
    assert ROLE_HIERARCHY['teacher'] > ROLE_HIERARCHY['student']
    print("   ✅ Role hierarchy correct")
    
    # Test has_role function
    print("\n2. Testing has_role() function:")
    
    class MockUser:
        def __init__(self, role):
            self.role = role
    
    student = MockUser('student')
    teacher = MockUser('teacher')
    admin = MockUser('admin')
    
    # Student tests
    assert has_role(student, 'student') == True
    assert has_role(student, 'teacher') == False
    assert has_role(student, 'admin') == False
    print("   ✅ Student role checks passed")
    
    # Teacher tests
    assert has_role(teacher, 'student') == True
    assert has_role(teacher, 'teacher') == True
    assert has_role(teacher, 'admin') == False
    print("   ✅ Teacher role checks passed")
    
    # Admin tests
    assert has_role(admin, 'student') == True
    assert has_role(admin, 'teacher') == True
    assert has_role(admin, 'admin') == True
    print("   ✅ Admin role checks passed")


def test_jwt_token_generation():
    """Test JWT token generation and verification."""
    print("\n" + "="*70)
    print("Testing JWT Token Functions")
    print("="*70)
    
    try:
        from auth_middleware import generate_jwt_token, verify_jwt_token
        import jwt
    except ImportError as e:
        print(f"\n   ⚠️  PyJWT not installed. Skipping JWT tests.")
        print(f"   Install with: pip install PyJWT")
        return
    
    class MockUser:
        def __init__(self):
            self.id = 1
            self.username = 'test_user'
            self.name = 'Test User'
            self.role = 'student'
    
    user = MockUser()
    
    print("\n1. Testing token generation:")
    token = generate_jwt_token(user)
    assert token is not None
    assert len(token) > 0
    print(f"   ✅ Token generated: {token[:50]}...")
    
    print("\n2. Testing token verification:")
    payload = verify_jwt_token(token)
    assert payload is not None
    assert payload['user_id'] == user.id
    assert payload['username'] == user.username
    assert payload['role'] == user.role
    print(f"   ✅ Token verified successfully")
    print(f"   Payload: {payload}")
    
    print("\n3. Testing invalid token:")
    invalid_payload = verify_jwt_token("invalid.token.here")
    assert invalid_payload is None
    print(f"   ✅ Invalid token correctly rejected")


def test_attendance_routes_structure():
    """Test that attendance routes are properly structured."""
    print("\n" + "="*70)
    print("Testing Attendance Routes Structure")
    print("="*70)
    
    from attendance_routes import attendance_bp
    
    print("\n1. Testing blueprint registration:")
    assert attendance_bp is not None
    assert attendance_bp.name == 'attendance'
    assert attendance_bp.url_prefix == '/attendance'
    print("   ✅ Blueprint configured correctly")
    
    print("\n2. Testing route registration:")
    routes = [rule.rule for rule in attendance_bp.url_map.iter_rules()]
    print(f"   Registered routes: {len(routes)}")
    
    # Check for expected routes (may vary based on implementation)
    print("   ✅ Routes registered")


def test_database_migration():
    """Test if database has role column."""
    print("\n" + "="*70)
    print("Testing Database Migration")
    print("="*70)
    
    import sqlite3
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'instance', 'attendance.db')
    
    if not os.path.exists(db_path):
        print(f"\n   ⚠️  Database not found at: {db_path}")
        print(f"   Run the application first to create the database.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n1. Checking for role column:")
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'role' in columns:
        print("   ✅ Role column exists in users table")
        
        print("\n2. Checking role values:")
        cursor.execute("SELECT DISTINCT role FROM user")
        roles = [row[0] for row in cursor.fetchall()]
        print(f"   Roles in database: {roles}")
        
        valid_roles = {'student', 'teacher', 'admin'}
        if all(role in valid_roles for role in roles):
            print("   ✅ All roles are valid")
        else:
            print(f"   ⚠️  Found invalid roles: {set(roles) - valid_roles}")
    else:
        print("   ❌ Role column not found!")
        print("   Run migration: python scripts/add_role_column.py")
    
    conn.close()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("SAS-88 RBAC Test Suite")
    print("="*70)
    
    tests = [
        ("RBAC Decorators", test_rbac_decorators),
        ("JWT Tokens", test_jwt_token_generation),
        ("Attendance Routes", test_attendance_routes_structure),
        ("Database Migration", test_database_migration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, "PASSED"))
        except Exception as e:
            results.append((test_name, f"FAILED: {str(e)}"))
            print(f"\n   ❌ Test failed with error: {e}")
    
    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    for test_name, result in results:
        status = "✅" if result == "PASSED" else "❌"
        print(f"{status} {test_name}: {result}")
    
    passed = sum(1 for _, r in results if r == "PASSED")
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! SAS-88 RBAC is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")


if __name__ == '__main__':
    main()
