"""Helper script to generate JWT tokens for testing SAS-88 RBAC.

This script generates JWT tokens for different user roles, which can be used
to test the JWT-based API endpoints without going through the login flow.
"""

import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import jwt
except ImportError:
    print("❌ PyJWT not installed. Please run: pip install PyJWT")
    sys.exit(1)


# JWT Configuration (should match auth_middleware.py)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_test_token(user_id, username, role, name, hours=24):
    """Generate a test JWT token."""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'name': name,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=hours)
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def print_token_info(role, token):
    """Print token information in a readable format."""
    print(f"\n{'='*70}")
    print(f"{role.upper()} TOKEN")
    print('='*70)
    print(f"\nToken:")
    print(token)
    print(f"\nDecoded Payload:")
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        for key, value in payload.items():
            if key in ['iat', 'exp']:
                dt = datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"  Error decoding: {e}")
    
    print(f"\nUsage:")
    print(f"  curl -H 'Authorization: Bearer {token}' \\")
    print(f"       http://localhost:5000/attendance/api/view")


def main():
    """Generate test tokens for all roles."""
    print("="*70)
    print("SAS-88 JWT Token Generator")
    print("="*70)
    print("\nGenerating test JWT tokens for all roles...")
    
    # Student token
    student_token = generate_test_token(
        user_id=1,
        username='PES1UG23CS001',
        role='student',
        name='Student One'
    )
    print_token_info('student', student_token)
    
    # Teacher token
    teacher_token = generate_test_token(
        user_id=2,
        username='FAC001',
        role='teacher',
        name='Prof. Smith'
    )
    print_token_info('teacher', teacher_token)
    
    # Admin token
    admin_token = generate_test_token(
        user_id=3,
        username='ADMIN001',
        role='admin',
        name='Admin User'
    )
    print_token_info('admin', admin_token)
    
    # Save tokens to file
    print("\n" + "="*70)
    print("Saving tokens to test_tokens.txt...")
    
    with open('test_tokens.txt', 'w') as f:
        f.write("SAS-88 Test JWT Tokens\n")
        f.write("="*70 + "\n\n")
        
        f.write("STUDENT TOKEN:\n")
        f.write(student_token + "\n\n")
        
        f.write("TEACHER TOKEN:\n")
        f.write(teacher_token + "\n\n")
        
        f.write("ADMIN TOKEN:\n")
        f.write(admin_token + "\n\n")
    
    print("✅ Tokens saved to test_tokens.txt")
    print("\n" + "="*70)
    print("\nTest the tokens with curl:")
    print("\nStudent (can only view):")
    print(f"  curl -H 'Authorization: Bearer {student_token[:50]}...' \\")
    print(f"       http://localhost:5000/attendance/api/view")
    print("\nTeacher (can view and mark):")
    print(f"  curl -X POST -H 'Authorization: Bearer {teacher_token[:50]}...' \\")
    print(f"       -H 'Content-Type: application/json' \\")
    print(f"       -d '{{\"student_id\":1,\"subject\":\"Math\",\"date\":\"2025-11-08\",\"status\":\"present\"}}' \\")
    print(f"       http://localhost:5000/attendance/api/mark")
    print("\nAdmin (can view, mark, and override):")
    print(f"  curl -X PUT -H 'Authorization: Bearer {admin_token[:50]}...' \\")
    print(f"       -H 'Content-Type: application/json' \\")
    print(f"       -d '{{\"attendance_id\":456,\"new_status\":\"present\",\"reason\":\"correction\"}}' \\")
    print(f"       http://localhost:5000/attendance/api/override")
    print()


if __name__ == '__main__':
    main()
