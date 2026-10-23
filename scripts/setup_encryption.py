#!/usr/bin/env python3
"""Setup script for multi-level encryption configuration.

This script helps configure encryption keys and security settings
for the Student Attendance Management System.

Features:
- Generate encryption keys
- Create .env file with secure defaults
- Generate TLS certificates for development
- Validate security configuration
- Test encryption functionality

Usage:
    python setup_encryption.py
"""

import os
import sys
import secrets
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def print_header(message):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70)


def generate_encryption_key():
    """Generate a new Fernet encryption key."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


def generate_secret_key():
    """Generate a secure random secret key."""
    return secrets.token_hex(32)


def create_env_file():
    """Create .env file with secure defaults."""
    print_header("Creating .env Configuration File")
    
    env_path = Path(__file__).parent.parent / '.env'
    
    if env_path.exists():
        response = input("\n⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("✅ Keeping existing .env file")
            return
    
    # Generate keys
    print("\n🔑 Generating encryption keys...")
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    jwt_secret = generate_secret_key()
    
    # Create .env content
    env_content = f"""# Student Attendance Management System - Security Configuration
# Generated on: {os.popen('date').read().strip()}

# ============================================================================
# CRITICAL SECURITY KEYS - DO NOT COMMIT TO VERSION CONTROL
# ============================================================================

# Flask secret key (for session encryption)
SECRET_KEY={secret_key}

# Encryption key for database fields (Fernet)
ENCRYPTION_KEY={encryption_key}

# JWT secret key for API authentication
JWT_SECRET_KEY={jwt_secret}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# SQLite (Development)
DATABASE_URL=sqlite:///instance/attendance.db

# PostgreSQL (Production - uncomment and configure)
# DATABASE_URL=postgresql://username:password@localhost:5432/attendance_db

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

# Environment: development, production, testing
FLASK_ENV=development

# Application name
SITE_NAME=PESU Attendance System

# ============================================================================
# TLS/HTTPS CONFIGURATION
# ============================================================================

# Enable TLS (HTTPS)
TLS_ENABLED=false

# TLS certificate paths (for production)
TLS_CERT_PATH=certs/server.crt
TLS_KEY_PATH=certs/server.key

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# Account locking
MAX_LOGIN_ATTEMPTS=3
ACCOUNT_LOCK_DURATION_MINUTES=30

# Password policy
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_DIGIT=true

# Log level
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# ============================================================================
# OPTIONAL: KEY ROTATION (for zero-downtime key rotation)
# ============================================================================

# Old encryption key (during rotation period)
# ENCRYPTION_KEY_OLD=

# ============================================================================
# TESTING & DEVELOPMENT
# ============================================================================

# Disable demo user seeding (set to 1 to disable)
# DISABLE_DEMO_SEED=0

# Reset demo passwords on startup (set to 1 to enable)
# RESET_DEMO_PASSWORDS=0

# Disable encryption (TESTING ONLY - NEVER IN PRODUCTION)
# DISABLE_ENCRYPTION=0
"""
    
    # Write to file
    env_path.write_text(env_content)
    
    print(f"\n✅ Created .env file at: {env_path}")
    print("\n📋 Configuration Summary:")
    print(f"   • Secret Key: {secret_key[:20]}... (64 chars)")
    print(f"   • Encryption Key: {encryption_key[:20]}... (44 chars)")
    print(f"   • JWT Secret: {jwt_secret[:20]}... (64 chars)")
    print("\n⚠️  IMPORTANT: Add .env to .gitignore to prevent accidental commit!")


def generate_tls_certificates():
    """Generate self-signed TLS certificates for development."""
    print_header("Generating TLS Certificates (Development)")
    
    certs_dir = Path(__file__).parent.parent / 'certs'
    cert_path = certs_dir / 'server.crt'
    key_path = certs_dir / 'server.key'
    
    if cert_path.exists() and key_path.exists():
        response = input("\n⚠️  TLS certificates already exist. Regenerate? (y/N): ")
        if response.lower() != 'y':
            print("✅ Keeping existing certificates")
            return
    
    # Create certs directory
    certs_dir.mkdir(exist_ok=True)
    
    print("\n🔐 Generating self-signed certificate...")
    print("   This may take a few moments...")
    
    try:
        # Generate certificate using OpenSSL
        result = subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-nodes',
            '-keyout', str(key_path),
            '-out', str(cert_path),
            '-days', '365',
            '-subj', '/CN=localhost/O=PESU/C=IN'
        ], capture_output=True, text=True, check=True)
        
        print(f"\n✅ TLS certificates generated:")
        print(f"   • Certificate: {cert_path}")
        print(f"   • Private Key: {key_path}")
        print(f"   • Valid for: 365 days")
        print("\n⚠️  These are self-signed certificates for development only!")
        print("   For production, use certificates from a trusted CA.")
        
    except FileNotFoundError:
        print("\n❌ OpenSSL not found. Please install OpenSSL:")
        print("   • macOS: brew install openssl")
        print("   • Ubuntu: sudo apt-get install openssl")
        print("   • Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to generate certificates: {e}")


def validate_configuration():
    """Validate security configuration."""
    print_header("Validating Security Configuration")
    
    try:
        from secure_config import SecureConfig
        
        validation = SecureConfig.validate_configuration()
        
        print("\n📊 Configuration Status:")
        print(f"   • Valid: {'✅ Yes' if validation['valid'] else '❌ No'}")
        print(f"   • Encryption Enabled: {'✅ Yes' if validation['encryption_enabled'] else '❌ No'}")
        print(f"   • TLS Enabled: {'✅ Yes' if validation['tls_enabled'] else '❌ No'}")
        print(f"   • HSTS Enabled: {'✅ Yes' if validation['hsts_enabled'] else '❌ No'}")
        print(f"   • CSRF Protection: {'✅ Yes' if validation['csrf_enabled'] else '❌ No'}")
        print(f"   • Log Sanitization: {'✅ Yes' if validation['log_sanitization_enabled'] else '❌ No'}")
        
        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"   • {warning}")
        
        if validation['errors']:
            print("\n❌ Errors:")
            for error in validation['errors']:
                print(f"   • {error}")
        
        if validation['valid']:
            print("\n✅ Configuration is valid!")
        else:
            print("\n❌ Configuration has errors. Please fix them before deployment.")
        
        return validation['valid']
        
    except ImportError as e:
        print(f"\n❌ Could not import configuration: {e}")
        return False


def test_encryption():
    """Test encryption functionality."""
    print_header("Testing Encryption Functionality")
    
    try:
        from encryption_utils import (
            encrypt_data, decrypt_data,
            hash_value, is_encryption_enabled,
            get_encryption_info
        )
        
        print("\n🔬 Running encryption tests...")
        
        # Test 1: Basic encryption
        print("\n1️⃣  Testing basic encryption/decryption...")
        test_data = "PES1UG23CS001"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        
        if decrypted == test_data:
            print("   ✅ Basic encryption: PASSED")
        else:
            print("   ❌ Basic encryption: FAILED")
            return False
        
        # Test 2: Hash function
        print("\n2️⃣  Testing deterministic hashing...")
        hash1 = hash_value("test_value")
        hash2 = hash_value("test_value")
        
        if hash1 == hash2 and len(hash1) == 64:
            print("   ✅ Hash function: PASSED")
        else:
            print("   ❌ Hash function: FAILED")
            return False
        
        # Test 3: Encryption info
        print("\n3️⃣  Testing encryption status...")
        info = get_encryption_info()
        print(f"   • Enabled: {info['enabled']}")
        print(f"   • Algorithm: {info['algorithm']}")
        print(f"   • Key Rotation: {info['key_rotation_supported']}")
        
        if is_encryption_enabled():
            print("   ✅ Encryption status: ENABLED")
        else:
            print("   ⚠️  Encryption status: DISABLED (OK for testing)")
        
        print("\n✅ All encryption tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_gitignore():
    """Ensure sensitive files are in .gitignore."""
    print_header("Updating .gitignore")
    
    gitignore_path = Path(__file__).parent.parent / '.gitignore'
    
    sensitive_patterns = [
        '.env',
        '.env.local',
        '.env.*.local',
        '*.key',
        '*.pem',
        'certs/',
        'logs/',
        'instance/',
        '__pycache__/',
        '*.pyc',
        '.coverage',
        'htmlcov/',
        '.pytest_cache/',
    ]
    
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
        new_patterns = [p for p in sensitive_patterns if p not in existing_content]
        
        if new_patterns:
            with open(gitignore_path, 'a') as f:
                f.write('\n# Security: Sensitive files\n')
                for pattern in new_patterns:
                    f.write(f'{pattern}\n')
            print(f"\n✅ Added {len(new_patterns)} patterns to .gitignore")
        else:
            print("\n✅ .gitignore already contains all sensitive patterns")
    else:
        gitignore_path.write_text('\n'.join(['# Security: Sensitive files'] + sensitive_patterns))
        print(f"\n✅ Created .gitignore with sensitive patterns")


def main():
    """Main setup function."""
    print_header("🔐 Multi-Level Encryption Setup")
    print("\nThis script will help you configure encryption for your application.")
    print("\nWhat would you like to do?")
    print("\n1. Full setup (recommended for first-time setup)")
    print("2. Generate encryption keys only")
    print("3. Generate TLS certificates only")
    print("4. Validate configuration")
    print("5. Test encryption")
    print("6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == '1':
        # Full setup
        create_gitignore()
        create_env_file()
        generate_tls_certificates()
        validate_configuration()
        test_encryption()
        
        print_header("✅ Setup Complete!")
        print("\n📝 Next Steps:")
        print("   1. Review the .env file and adjust settings as needed")
        print("   2. For production, replace self-signed certificates with CA-signed ones")
        print("   3. Run: python setup_database.py (to initialize database)")
        print("   4. Run: python src/main.py (to start the application)")
        print("\n⚠️  Remember: NEVER commit .env file or certificates to version control!")
        
    elif choice == '2':
        create_env_file()
        
    elif choice == '3':
        generate_tls_certificates()
        
    elif choice == '4':
        validate_configuration()
        
    elif choice == '5':
        test_encryption()
        
    elif choice == '6':
        print("\n👋 Goodbye!")
        return
        
    else:
        print("\n❌ Invalid choice. Please run the script again.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
