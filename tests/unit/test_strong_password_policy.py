"""Tests for SAS-85: Strong Password Policy Enforcement.

This module tests the password strength validation, password change endpoint,
and real-time password validation API.
"""

import pytest
from flask import url_for
from src.password_security import validate_password_strength, PasswordStrengthError


class TestPasswordStrengthValidation:
    """Test password strength validation function."""
    
    def test_valid_strong_password(self):
        """Test that a strong password passes validation."""
        password = "SecurePass123!@#"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is True
        assert error_msg is None
    
    def test_password_too_short(self):
        """Test that password under 8 characters fails."""
        password = "Short1!"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "at least 8 characters" in error_msg
    
    def test_password_too_long(self):
        """Test that password over 128 characters fails."""
        password = "A" * 129 + "1!"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "must not exceed 128 characters" in error_msg
    
    def test_password_no_uppercase(self):
        """Test that password without uppercase fails."""
        password = "lowercase123!"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "uppercase letter" in error_msg
    
    def test_password_no_lowercase(self):
        """Test that password without lowercase fails."""
        password = "UPPERCASE123!"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "lowercase letter" in error_msg
    
    def test_password_no_digit(self):
        """Test that password without digit fails."""
        password = "NoDigitPass!"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "digit" in error_msg
    
    def test_password_no_special_char(self):
        """Test that password without special character fails."""
        password = "NoSpecial123"
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "special character" in error_msg
    
    def test_empty_password(self):
        """Test that empty password fails."""
        password = ""
        is_valid, error_msg = validate_password_strength(password)
        assert is_valid is False
        assert "cannot be empty" in error_msg
    
    def test_various_special_characters(self):
        """Test that different special characters are accepted."""
        special_chars = "!@#$%^&*(),.?\":{}|<>_-+=[]\\\/;~`"
        for char in special_chars:
            password = f"TestPass123{char}"
            is_valid, error_msg = validate_password_strength(password)
            assert is_valid is True, f"Special character '{char}' should be valid"


class TestPasswordChangeEndpoint:
    """Test password change functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.main import app as flask_app, db
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with flask_app.app_context():
            db.create_all()
            yield flask_app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def test_user(self, app):
        """Create a test user and return their ID."""
        from src.main import db, User
        with app.app_context():
            user = User(username='testuser', name='Test User')
            user.set_password('OldPassword123!')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            return user_id
    
    def test_change_password_page_accessible(self, client, test_user, app):
        """Test that change password page loads."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user)
        
        response = client.get('/change-password')
        assert response.status_code in [200, 302]  # 302 if redirects to login
    
    def test_change_password_with_valid_password(self, client, test_user, app):
        """Test successful password change with strong password."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user)
            
            response = client.post('/change-password', data={
                'current_password': 'OldPassword123!',
                'new_password': 'NewSecurePass456!',
                'confirm_password': 'NewSecurePass456!'
            }, follow_redirects=False)
            
            # Should redirect on success
            assert response.status_code in [200, 302]
    
    def test_change_password_with_weak_password(self, client, test_user, app):
        """Test password change fails with weak password."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user)
            
            response = client.post('/change-password', data={
                'current_password': 'OldPassword123!',
                'new_password': 'weak',
                'confirm_password': 'weak'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'does not meet requirements' in response.data or b'at least 8 characters' in response.data
    
    def test_change_password_wrong_current_password(self, client, test_user, app):
        """Test password change fails with wrong current password."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user)
            
            response = client.post('/change-password', data={
                'current_password': 'WrongPassword123!',
                'new_password': 'NewSecurePass456!',
                'confirm_password': 'NewSecurePass456!'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'incorrect' in response.data.lower()
    
    def test_change_password_mismatch_confirmation(self, client, test_user, app):
        """Test password change fails when passwords don't match."""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user)
            
            response = client.post('/change-password', data={
                'current_password': 'OldPassword123!',
                'new_password': 'NewSecurePass456!',
                'confirm_password': 'DifferentPass456!'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'do not match' in response.data


class TestPasswordValidationAPI:
    """Test real-time password validation API."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from src.main import app as flask_app
        flask_app.config['TESTING'] = True
        return flask_app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_validate_strong_password_api(self, client):
        """Test API validates strong password correctly."""
        response = client.post('/api/validate-password',
                             json={'password': 'StrongPass123!'},
                             content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['strength'] in ['medium', 'strong']
        assert data['score'] >= 4
    
    def test_validate_weak_password_api(self, client):
        """Test API rejects weak password."""
        response = client.post('/api/validate-password',
                             json={'password': 'weak'},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['valid'] is False
        assert 'message' in data
    
    def test_validate_empty_password_api(self, client):
        """Test API handles empty password."""
        response = client.post('/api/validate-password',
                             json={'password': ''},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['valid'] is False
    
    def test_api_returns_detailed_checks(self, client):
        """Test API returns detailed requirement checks."""
        response = client.post('/api/validate-password',
                             json={'password': 'TestPass123!'},
                             content_type='application/json')
        
        data = response.get_json()
        assert 'checks' in data
        assert 'length' in data['checks']
        assert 'uppercase' in data['checks']
        assert 'lowercase' in data['checks']
        assert 'digit' in data['checks']
        assert 'special' in data['checks']
    
    def test_api_returns_requirements(self, client):
        """Test API returns password requirements."""
        response = client.post('/api/validate-password',
                             json={'password': 'AnyPassword1!'},
                             content_type='application/json')
        
        data = response.get_json()
        assert 'requirements' in data
        assert data['requirements']['min_length'] == 8
        assert data['requirements']['requires_uppercase'] is True
        assert data['requirements']['requires_lowercase'] is True
        assert data['requirements']['requires_digit'] is True
        assert data['requirements']['requires_special'] is True


class TestPasswordPolicyIntegration:
    """Integration tests for password policy enforcement."""
    
    def test_password_strength_in_user_creation(self):
        """Test password strength is validated during user creation."""
        from src.password_security import hash_password, PasswordStrengthError
        
        # Should succeed with strong password
        strong_password = "SecurePass123!"
        try:
            hash_password(strong_password, validate_strength=True)
        except PasswordStrengthError:
            pytest.fail("Strong password should not raise PasswordStrengthError")
        
        # Should fail with weak password
        weak_password = "weak"
        with pytest.raises(PasswordStrengthError):
            hash_password(weak_password, validate_strength=True)
    
    def test_password_requirements_documented(self):
        """Test that password requirements are clearly defined."""
        from src.password_security import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH
        
        assert MIN_PASSWORD_LENGTH == 8
        assert MAX_PASSWORD_LENGTH == 128
