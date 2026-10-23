"""Secure Configuration Module for Multi-Level Encryption.

This module provides secure configuration management ensuring encryption
at all levels: at rest, in transit, and in use.

Security Features:
1. DATA AT REST:
   - Database field encryption using Fernet (AES-128)
   - Encrypted audit logs
   - Encrypted session data
   - Secure password hashing with bcrypt

2. DATA IN TRANSIT:
   - TLS/HTTPS enforcement
   - Secure cookie configuration
   - HSTS headers
   - Certificate pinning support

3. DATA IN USE:
   - Log sanitization
   - Memory clearing for sensitive data
   - Input validation and sanitization
   - Protection against timing attacks

Configuration Priority:
1. Environment variables (.env file)
2. System environment
3. Secure defaults

Environment Variables Required:
- SECRET_KEY: Flask session secret (32+ chars random)
- ENCRYPTION_KEY: Data encryption key (Fernet key)
- DATABASE_URL: Database connection string
- TLS_CERT_PATH: Path to TLS certificate (production)
- TLS_KEY_PATH: Path to TLS private key (production)
"""

import os
import secrets
from typing import Dict, Any, Optional
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SecureConfig:
    """Secure configuration class with encryption at all levels."""

    # ========================================================================
    # CORE SECURITY SETTINGS
    # ========================================================================

    # Flask secret key for session encryption (DATA AT REST - Session Storage)
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)

    # Encryption key for database fields (DATA AT REST - Database)
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    ENCRYPTION_KEY_OLD = os.getenv('ENCRYPTION_KEY_OLD')  # For key rotation

    # Security headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files

    # ========================================================================
    # DATABASE CONFIGURATION (DATA AT REST)
    # ========================================================================

    # Database URI with connection pooling
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///instance/attendance.db'
    )

    # Database connection security
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'timeout': 30,  # SQLite timeout
        }
    }

    # ========================================================================
    # SESSION CONFIGURATION (DATA AT REST & IN TRANSIT)
    # ========================================================================

    # Session security
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SESSION_COOKIE_NAME = '__Host-session'  # Secure cookie naming
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # Remember me cookie security
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_NAME = '__Host-remember_token'

    # ========================================================================
    # TLS/HTTPS CONFIGURATION (DATA IN TRANSIT)
    # ========================================================================

    # TLS/SSL Configuration
    TLS_ENABLED = os.getenv('TLS_ENABLED', 'true').lower() == 'true'
    TLS_CERT_PATH = os.getenv('TLS_CERT_PATH', 'certs/server.crt')
    TLS_KEY_PATH = os.getenv('TLS_KEY_PATH', 'certs/server.key')

    # Minimum TLS version
    TLS_MIN_VERSION = 'TLSv1.2'

    # HSTS (HTTP Strict Transport Security)
    HSTS_ENABLED = True
    HSTS_MAX_AGE = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS = True
    HSTS_PRELOAD = True

    # ========================================================================
    # CSRF PROTECTION (DATA IN TRANSIT)
    # ========================================================================

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token validity
    WTF_CSRF_SSL_STRICT = True  # Enforce HTTPS for CSRF
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # ========================================================================
    # PASSWORD SECURITY (DATA AT REST)
    # ========================================================================

    # Bcrypt configuration
    BCRYPT_LOG_ROUNDS = 12  # 2^12 iterations (secure but not too slow)

    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = False

    # Account locking
    MAX_LOGIN_ATTEMPTS = 3
    ACCOUNT_LOCK_DURATION = timedelta(minutes=30)

    # ========================================================================
    # API SECURITY (DATA IN TRANSIT)
    # ========================================================================

    # JWT token configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    JWT_REFRESH_EXPIRATION_DAYS = 7

    # API rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = "memory://"

    # ========================================================================
    # LOGGING SECURITY (DATA IN USE)
    # ========================================================================

    # Log sanitization
    LOG_SANITIZATION_ENABLED = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

    # Sensitive fields to sanitize in logs
    SENSITIVE_FIELDS = [
        'password',
        'token',
        'api_key',
        'secret',
        'private_key',
        'credit_card',
        'ssn',
        'access_token',
        'refresh_token'
    ]

    # ========================================================================
    # AUDIT TRAIL (DATA AT REST)
    # ========================================================================

    # Encrypt audit logs
    AUDIT_LOG_ENCRYPTION = True
    AUDIT_LOG_RETENTION_DAYS = 90

    # Fields to encrypt in audit logs
    AUDIT_ENCRYPTED_FIELDS = [
        'ip_address',
        'user_agent',
        'changes',
        'old_values',
        'new_values',
        'reason'
    ]

    # ========================================================================
    # CONTENT SECURITY POLICY (DATA IN TRANSIT)
    # ========================================================================

    CSP_ENABLED = True
    CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",  # TODO: Remove unsafe-inline in production
        'style-src': "'self' 'unsafe-inline'",   # TODO: Remove unsafe-inline in production
        'img-src': "'self' data: https:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'"
    }

    # ========================================================================
    # ENVIRONMENT-SPECIFIC OVERRIDES
    # ========================================================================

    @staticmethod
    def init_app(app):
        """Initialize application with secure configuration.
        
        Args:
            app: Flask application instance
        """
        # Set secure headers
        @app.after_request
        def set_security_headers(response):
            """Add security headers to all responses."""
            # HSTS
            if SecureConfig.HSTS_ENABLED:
                hsts_value = f'max-age={SecureConfig.HSTS_MAX_AGE}'
                if SecureConfig.HSTS_INCLUDE_SUBDOMAINS:
                    hsts_value += '; includeSubDomains'
                if SecureConfig.HSTS_PRELOAD:
                    hsts_value += '; preload'
                response.headers['Strict-Transport-Security'] = hsts_value

            # Content Security Policy
            if SecureConfig.CSP_ENABLED:
                csp_value = '; '.join([
                    f"{key} {value}"
                    for key, value in SecureConfig.CONTENT_SECURITY_POLICY.items()
                ])
                response.headers['Content-Security-Policy'] = csp_value

            # Other security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

            return response

        return app

    @staticmethod
    def validate_configuration() -> Dict[str, Any]:
        """Validate security configuration and return status.
        
        Returns:
            Dictionary with validation results and warnings
        """
        warnings = []
        errors = []

        # Check SECRET_KEY strength
        if len(SecureConfig.SECRET_KEY) < 32:
            warnings.append("SECRET_KEY should be at least 32 characters")

        # Check ENCRYPTION_KEY presence
        if not SecureConfig.ENCRYPTION_KEY:
            errors.append("ENCRYPTION_KEY is not set - encryption will use temporary key")

        # Check TLS configuration
        if not SecureConfig.TLS_ENABLED:
            warnings.append("TLS is disabled - data in transit is not encrypted")

        # Check production settings
        if os.getenv('FLASK_ENV') == 'production':
            if not SecureConfig.TLS_ENABLED:
                errors.append("TLS must be enabled in production")
            if not SecureConfig.SESSION_COOKIE_SECURE:
                errors.append("SESSION_COOKIE_SECURE must be True in production")

        return {
            'valid': len(errors) == 0,
            'warnings': warnings,
            'errors': errors,
            'encryption_enabled': SecureConfig.ENCRYPTION_KEY is not None,
            'tls_enabled': SecureConfig.TLS_ENABLED,
            'hsts_enabled': SecureConfig.HSTS_ENABLED,
            'csrf_enabled': SecureConfig.WTF_CSRF_ENABLED,
            'log_sanitization_enabled': SecureConfig.LOG_SANITIZATION_ENABLED,
        }


class DevelopmentConfig(SecureConfig):
    """Development configuration with relaxed security for local testing."""

    DEBUG = True
    TESTING = False

    # Allow insecure cookies for local development
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False

    # Disable TLS for local dev (use TLS wrapper for testing)
    TLS_ENABLED = False


class ProductionConfig(SecureConfig):
    """Production configuration with maximum security."""

    DEBUG = False
    TESTING = False

    # Force HTTPS
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True

    # Enable all security features
    TLS_ENABLED = True
    HSTS_ENABLED = True
    CSP_ENABLED = True
    AUDIT_LOG_ENCRYPTION = True
    LOG_SANITIZATION_ENABLED = True


class TestingConfig(SecureConfig):
    """Testing configuration with minimal security for fast tests."""

    DEBUG = False
    TESTING = True

    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable security features for faster tests
    WTF_CSRF_ENABLED = False
    TLS_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4  # Faster password hashing

    # Disable encryption for tests (optional)
    # ENCRYPTION_KEY can still be set for encryption tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: Optional[str] = None) -> SecureConfig:
    """Get configuration for specified environment.
    
    Args:
        env: Environment name (development, production, testing)
    
    Returns:
        Configuration class for the environment
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')

    return config.get(env, config['default'])
