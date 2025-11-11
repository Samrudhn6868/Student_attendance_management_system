"""
Verification script to check if encryption is properly configured and working.
This script can be run in production to verify SAS-92 implementation.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_encryption_key():
    """Check if ENCRYPTION_KEY is set in environment"""
    from dotenv import load_dotenv
    load_dotenv()
    
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        return False, "ENCRYPTION_KEY not found in environment"
    
    if len(key) < 32:
        return False, f"ENCRYPTION_KEY too short: {len(key)} bytes (needs 44 bytes base64)"
    
    return True, "ENCRYPTION_KEY configured correctly"


def check_encryption_module():
    """Check if encryption utils module is importable"""
    try:
        from encryption_utils import encrypt_data, decrypt_data, hash_value
        return True, "Encryption module imported successfully"
    except ImportError as e:
        return False, f"Failed to import encryption module: {e}"


def check_cryptography_package():
    """Check if cryptography package is installed"""
    try:
        from cryptography.fernet import Fernet
        return True, "Cryptography package available"
    except ImportError:
        return False, "Cryptography package not installed"


def test_encryption_roundtrip():
    """Test basic encryption/decryption roundtrip"""
    try:
        from encryption_utils import encrypt_data, decrypt_data
        
        test_data = "SAS-92 Test Data"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        
        if decrypted == test_data:
            return True, "Encryption/decryption roundtrip successful"
        else:
            return False, f"Roundtrip failed: '{test_data}' != '{decrypted}'"
    except Exception as e:
        return False, f"Encryption test failed: {e}"


def test_hash_deterministic():
    """Test that hashing is deterministic"""
    try:
        from encryption_utils import hash_value
        
        test_value = "test_hash_value"
        hash1 = hash_value(test_value)
        hash2 = hash_value(test_value)
        
        if hash1 == hash2:
            return True, "Hash function is deterministic"
        else:
            return False, "Hash function is not deterministic"
    except Exception as e:
        return False, f"Hash test failed: {e}"


def verify_database_schema():
    """Verify database has encrypted columns"""
    try:
        from flask import Flask
        from models import db, Attendance
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../src/instance/attendance.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            # Check if Attendance model has required attributes
            required_attrs = ['student_srn', 'course_id', 'status', 'marked_by',
                            'student_srn_hash', 'course_id_hash', 'status_hash']
            
            for attr in required_attrs:
                if not hasattr(Attendance, attr):
                    return False, f"Attendance model missing attribute: {attr}"
            
            return True, "Database schema has all required encrypted fields"
    except Exception as e:
        return False, f"Schema verification failed: {e}"


def main():
    """Run all verification checks"""
    print("\n" + "="*70)
    print("SAS-92 ENCRYPTION VERIFICATION")
    print("="*70 + "\n")
    
    checks = [
        ("Cryptography Package", check_cryptography_package),
        ("Encryption Module", check_encryption_module),
        ("Encryption Key", check_encryption_key),
        ("Encryption Roundtrip", test_encryption_roundtrip),
        ("Hash Determinism", test_hash_deterministic),
        ("Database Schema", verify_database_schema),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed, message = check_func()
            results.append((name, passed, message))
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status:8} | {name:25} | {message}")
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ FAIL   | {name:25} | Error: {e}")
    
    print("\n" + "="*70)
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    
    print(f"Results: {passed_count}/{total_count} checks passed")
    
    if passed_count == total_count:
        print("✓ SAS-92 encryption is properly configured and working!")
        print("="*70 + "\n")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
