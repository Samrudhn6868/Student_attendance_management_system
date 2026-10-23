"""Unit tests for secure_config.py - Security Configuration."""

import pytest
import os
from datetime import timedelta
from src.secure_config import (
    SecureConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config
)


class TestSecureConfig:
    """Test SecureConfig base class."""
    
    def test_secret_key_exists(self):
        """Test that SECRET_KEY is set."""
        assert SecureConfig.SECRET_KEY is not None
        assert len(SecureConfig.SECRET_KEY) >= 32
    
    def test_database_uri(self):
        """Test database URI configuration."""
        assert SecureConfig.SQLALCHEMY_DATABASE_URI is not None
        assert 'sqlite:///' in SecureConfig.SQLALCHEMY_DATABASE_URI
    
    def test_session_security_settings(self):
        """Test session cookie security settings."""
        assert SecureConfig.SESSION_COOKIE_SECURE is True
        assert SecureConfig.SESSION_COOKIE_HTTPONLY is True
        assert SecureConfig.SESSION_COOKIE_SAMESITE == 'Lax'
        assert SecureConfig.SESSION_COOKIE_NAME == '__Host-session'
    
    def test_remember_cookie_security(self):
        """Test remember me cookie security settings."""
        assert SecureConfig.REMEMBER_COOKIE_SECURE is True
        assert SecureConfig.REMEMBER_COOKIE_HTTPONLY is True
        assert isinstance(SecureConfig.REMEMBER_COOKIE_DURATION, timedelta)
    
    def test_tls_configuration(self):
        """Test TLS/SSL configuration."""
        assert SecureConfig.TLS_MIN_VERSION == 'TLSv1.2'
        assert SecureConfig.HSTS_ENABLED is True
        assert SecureConfig.HSTS_MAX_AGE == 31536000
        assert SecureConfig.HSTS_INCLUDE_SUBDOMAINS is True
    
    def test_csrf_protection(self):
        """Test CSRF protection settings."""
        assert SecureConfig.WTF_CSRF_ENABLED is True
        assert SecureConfig.WTF_CSRF_TIME_LIMIT == 3600
        assert SecureConfig.WTF_CSRF_SSL_STRICT is True
    
    def test_password_policy(self):
        """Test password policy settings."""
        assert SecureConfig.PASSWORD_MIN_LENGTH == 8
        assert SecureConfig.PASSWORD_REQUIRE_UPPERCASE is True
        assert SecureConfig.PASSWORD_REQUIRE_LOWERCASE is True
        assert SecureConfig.PASSWORD_REQUIRE_DIGIT is True
    
    def test_account_locking(self):
        """Test account locking settings."""
        assert SecureConfig.MAX_LOGIN_ATTEMPTS == 3
        assert isinstance(SecureConfig.ACCOUNT_LOCK_DURATION, timedelta)
        assert SecureConfig.ACCOUNT_LOCK_DURATION.total_seconds() == 1800
    
    def test_bcrypt_rounds(self):
        """Test bcrypt configuration."""
        assert SecureConfig.BCRYPT_LOG_ROUNDS == 12
    
    def test_jwt_configuration(self):
        """Test JWT token settings."""
        assert SecureConfig.JWT_ALGORITHM == 'HS256'
        assert SecureConfig.JWT_EXPIRATION_HOURS == 24
        assert SecureConfig.JWT_REFRESH_EXPIRATION_DAYS == 7
    
    def test_log_sanitization_settings(self):
        """Test log sanitization configuration."""
        assert SecureConfig.LOG_SANITIZATION_ENABLED is True
        assert 'password' in SecureConfig.SENSITIVE_FIELDS
        assert 'token' in SecureConfig.SENSITIVE_FIELDS
        assert 'api_key' in SecureConfig.SENSITIVE_FIELDS
    
    def test_audit_trail_settings(self):
        """Test audit trail configuration."""
        assert SecureConfig.AUDIT_LOG_ENCRYPTION is True
        assert SecureConfig.AUDIT_LOG_RETENTION_DAYS == 90
        assert 'ip_address' in SecureConfig.AUDIT_ENCRYPTED_FIELDS
    
    def test_csp_configuration(self):
        """Test Content Security Policy settings."""
        assert SecureConfig.CSP_ENABLED is True
        assert 'default-src' in SecureConfig.CONTENT_SECURITY_POLICY
        assert 'frame-ancestors' in SecureConfig.CONTENT_SECURITY_POLICY
        assert SecureConfig.CONTENT_SECURITY_POLICY['frame-ancestors'] == "'none'"
    
    def test_database_engine_options(self):
        """Test database connection pool settings."""
        options = SecureConfig.SQLALCHEMY_ENGINE_OPTIONS
        assert options['pool_pre_ping'] is True
        assert options['pool_recycle'] == 3600
        assert options['pool_size'] == 10
    
    def test_validate_configuration(self):
        """Test configuration validation method."""
        result = SecureConfig.validate_configuration()
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'warnings' in result
        assert 'errors' in result
        assert 'encryption_enabled' in result
        assert 'tls_enabled' in result
    
    def test_validate_configuration_warnings(self):
        """Test configuration validation returns warnings."""
        result = SecureConfig.validate_configuration()
        assert isinstance(result['warnings'], list)
        assert isinstance(result['errors'], list)


class TestDevelopmentConfig:
    """Test DevelopmentConfig class."""
    
    def test_debug_enabled(self):
        """Test DEBUG is enabled in development."""
        assert DevelopmentConfig.DEBUG is True
    
    def test_testing_disabled(self):
        """Test TESTING is disabled in development."""
        assert DevelopmentConfig.TESTING is False
    
    def test_relaxed_cookie_security(self):
        """Test cookie security is relaxed for local dev."""
        assert DevelopmentConfig.SESSION_COOKIE_SECURE is False
        assert DevelopmentConfig.REMEMBER_COOKIE_SECURE is False
        assert DevelopmentConfig.WTF_CSRF_SSL_STRICT is False
    
    def test_tls_disabled(self):
        """Test TLS is disabled for local development."""
        assert DevelopmentConfig.TLS_ENABLED is False
    
    def test_inherits_from_secure_config(self):
        """Test DevelopmentConfig inherits from SecureConfig."""
        assert issubclass(DevelopmentConfig, SecureConfig)
        assert DevelopmentConfig.BCRYPT_LOG_ROUNDS == 12
        assert DevelopmentConfig.PASSWORD_MIN_LENGTH == 8


class TestProductionConfig:
    """Test ProductionConfig class."""
    
    def test_debug_disabled(self):
        """Test DEBUG is disabled in production."""
        assert ProductionConfig.DEBUG is False
    
    def test_testing_disabled(self):
        """Test TESTING is disabled in production."""
        assert ProductionConfig.TESTING is False
    
    def test_strict_cookie_security(self):
        """Test cookie security is strict in production."""
        assert ProductionConfig.SESSION_COOKIE_SECURE is True
        assert ProductionConfig.REMEMBER_COOKIE_SECURE is True
        assert ProductionConfig.WTF_CSRF_SSL_STRICT is True
    
    def test_tls_enabled(self):
        """Test TLS is enabled in production."""
        assert ProductionConfig.TLS_ENABLED is True
    
    def test_all_security_enabled(self):
        """Test all security features are enabled in production."""
        assert ProductionConfig.HSTS_ENABLED is True
        assert ProductionConfig.CSP_ENABLED is True
        assert ProductionConfig.AUDIT_LOG_ENCRYPTION is True
        assert ProductionConfig.LOG_SANITIZATION_ENABLED is True
    
    def test_inherits_from_secure_config(self):
        """Test ProductionConfig inherits from SecureConfig."""
        assert issubclass(ProductionConfig, SecureConfig)


class TestTestingConfig:
    """Test TestingConfig class."""
    
    def test_debug_disabled(self):
        """Test DEBUG is disabled in testing."""
        assert TestingConfig.DEBUG is False
    
    def test_testing_enabled(self):
        """Test TESTING is enabled."""
        assert TestingConfig.TESTING is True
    
    def test_in_memory_database(self):
        """Test uses in-memory database for tests."""
        assert TestingConfig.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'
    
    def test_csrf_disabled(self):
        """Test CSRF is disabled for faster tests."""
        assert TestingConfig.WTF_CSRF_ENABLED is False
    
    def test_tls_disabled(self):
        """Test TLS is disabled for tests."""
        assert TestingConfig.TLS_ENABLED is False
    
    def test_fast_bcrypt(self):
        """Test bcrypt uses fewer rounds for faster tests."""
        assert TestingConfig.BCRYPT_LOG_ROUNDS == 4
    
    def test_inherits_from_secure_config(self):
        """Test TestingConfig inherits from SecureConfig."""
        assert issubclass(TestingConfig, SecureConfig)


class TestGetConfig:
    """Test get_config function."""
    
    def test_get_development_config(self):
        """Test getting development configuration."""
        config = get_config('development')
        assert config == DevelopmentConfig
    
    def test_get_production_config(self):
        """Test getting production configuration."""
        config = get_config('production')
        assert config == ProductionConfig
    
    def test_get_testing_config(self):
        """Test getting testing configuration."""
        config = get_config('testing')
        assert config == TestingConfig
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_config()
        assert config == DevelopmentConfig
    
    def test_get_invalid_config_returns_default(self):
        """Test invalid config name returns default."""
        config = get_config('invalid')
        assert config == DevelopmentConfig


class TestSecurityHeaders:
    """Test security headers initialization."""
    
    def test_init_app_returns_app(self):
        """Test init_app returns the app object."""
        from flask import Flask
        app = Flask(__name__)
        result = SecureConfig.init_app(app)
        assert result == app
    
    def test_init_app_adds_security_headers(self):
        """Test init_app adds security header middleware."""
        from flask import Flask
        app = Flask(__name__)
        SecureConfig.init_app(app)
        
        # Check that after_request handler was added
        assert len(app.after_request_funcs[None]) > 0


class TestConfigurationValidation:
    """Test configuration validation logic."""
    
    def test_validation_checks_secret_key(self):
        """Test validation checks SECRET_KEY length."""
        result = SecureConfig.validate_configuration()
        # If SECRET_KEY is less than 32 chars, should have warning
        if len(SecureConfig.SECRET_KEY) < 32:
            assert any('SECRET_KEY' in w for w in result['warnings'])
    
    def test_validation_checks_encryption_key(self):
        """Test validation checks ENCRYPTION_KEY presence."""
        result = SecureConfig.validate_configuration()
        assert 'encryption_enabled' in result
    
    def test_validation_checks_tls(self):
        """Test validation checks TLS settings."""
        result = SecureConfig.validate_configuration()
        assert 'tls_enabled' in result
    
    def test_validation_checks_hsts(self):
        """Test validation checks HSTS settings."""
        result = SecureConfig.validate_configuration()
        assert 'hsts_enabled' in result
    
    def test_validation_checks_csrf(self):
        """Test validation checks CSRF settings."""
        result = SecureConfig.validate_configuration()
        assert 'csrf_enabled' in result
    
    def test_validation_checks_log_sanitization(self):
        """Test validation checks log sanitization."""
        result = SecureConfig.validate_configuration()
        assert 'log_sanitization_enabled' in result
